"""
TwoStageExecutor - Two-Stage查询执行器
负责协调整个查询流程：Stage 1(文档级理解) + Stage 2(综合答案)
"""
from typing import List, Dict, AsyncGenerator
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.database import Document
from app.services.document_loader import DocumentLoader
from app.services.document_processor import DocumentProcessor
from app.services.reference_extractor import ReferenceExtractor, Stage1Result
from app.utils.bedrock_client import BedrockClient

logger = get_logger(__name__)


# Prompt模板
STAGE1_PROMPT_TEMPLATE = """以下是一份产品文档的完整内容，包含文字和图片。
文档中的每个段落都有标记 [DOC-{doc_short_id}-PARA-X]，每张图片都有标记 [DOC-{doc_short_id}-IMAGE-X]。

请仔细阅读文档（包括图片中的信息），然后按照以下格式回复：

## 文档结构
[简要描述文档的主题、版本、日期等元信息，1-2句话]
[列出文档的主要分块，每个分块一行，格式：- [DOC-xxx-PARA-X] 分块主题]

## query的回复
[基于本文档内容回答用户问题，务必在相关内容后标注引用来源，例如：根据[DOC-xxx-PARA-5]的描述...]

## 引用
[列出所有引用的段落和图片，每个引用占一行：]
[DOC-xxx-PARA-X] 段落完整内容...
[DOC-xxx-IMAGE-X] 图片文件名

用户问题：{query}
"""

STAGE2_PROMPT_TEMPLATE = """我已经让{doc_count}个助手分别阅读了相关文档，并基于这些文档回答了用户的问题。

以下是每个助手的回复：

{all_stage1_responses}

现在请你综合这些回复，给出一个完整、准确、结构清晰的最终答案。

**输出格式要求**：
请使用Markdown格式输出，包含两个部分：

## 综合回复
[在这里给出完整答案，必须在相关内容后标注引用来源，例如：根据[DOC-xxx-PARA-5]的描述...]
[如果引用图片，使用 [DOC-xxx-IMAGE-X] 标记]

## 引用文档

### 文档1：[文档名称]
- [DOC-xxx-PARA-X] 段落内容...
- [DOC-xxx-IMAGE-X] 图片：filename.png

### 文档2：[文档名称]
- ...

**关键要求**：
1. **必须保持引用标记**：每次提到文档中的信息时，必须在相关句子后添加引用标记，格式为 [DOC-xxx-PARA-X] 或 [DOC-xxx-IMAGE-X]
   - 例如："登录功能支持手机号和邮箱[DOC-abc12345-PARA-3]"
   - 例如："如下图所示[DOC-abc12345-IMAGE-1]，系统架构包含..."
2. 如果多个文档的回复有冲突，请指出差异并说明可能的原因
3. 如果多个文档的回复互补，请整合成完整答案
4. 答案要自然流畅，不要简单罗列
5. 在"引用文档"部分，列出所有在"综合回复"中引用的段落和图片
6. 图片引用格式：- [DOC-xxx-IMAGE-X] 图片：filename.png

用户问题：{query}
"""


class TwoStageExecutor:
    """Two-Stage查询执行器"""

    def __init__(
        self,
        db_session: Session,
        bedrock_client: BedrockClient
    ):
        """
        初始化TwoStageExecutor

        Args:
            db_session: 数据库会话
            bedrock_client: Bedrock客户端
        """
        self.db = db_session
        self.bedrock_client = bedrock_client

        # 初始化子模块
        self.doc_loader = DocumentLoader(db_session)
        self.doc_processor = DocumentProcessor()
        self.ref_extractor = ReferenceExtractor()

        logger.info("two_stage_executor_initialized")

    async def execute_streaming(
        self,
        query: str,
        document_ids: List[str]
    ) -> AsyncGenerator[Dict, None]:
        """
        执行Two-Stage查询，流式返回结果

        Args:
            query: 用户问题
            document_ids: 要处理的文档ID列表

        Yields:
            SSE事件字典：
            - {"type": "progress", "data": {...}}
            - {"type": "answer_delta", "data": {"text": "..."}}
            - {"type": "references", "data": [...]}
            - {"type": "done", "data": {"tokens": {...}}}
            - {"type": "error", "data": {"message": "..."}}
        """
        logger.info(
            "start_two_stage_execution",
            query=query[:100],
            document_count=len(document_ids)
        )

        try:
            # Stage 1: 串行处理每个文档
            stage1_results = []

            for idx, doc_id in enumerate(document_ids, 1):
                # 检查文档是否存在且未删除
                doc = self.db.query(Document).filter(Document.id == doc_id).first()

                if not doc:
                    logger.warning("document_not_found", doc_id=doc_id)
                    continue

                if doc.status == "deleted":
                    logger.warning("document_deleted_skipping", doc_id=doc_id, filename=doc.filename)
                    continue

                doc_name = doc.filename

                yield {
                    "type": "progress",
                    "data": {
                        "current": idx,
                        "total": len(document_ids),
                        "doc_name": doc_name
                    }
                }

                # 处理单个文档
                try:
                    logger.info(
                        "processing_document_stage1",
                        doc_id=doc_id,
                        index=idx,
                        total=len(document_ids)
                    )

                    result = await self._process_single_document(query, doc_id)
                    stage1_results.append(result)

                    logger.info(
                        "document_stage1_completed",
                        doc_id=doc_id,
                        doc_name=result.doc_name,
                        doc_short_id=result.doc_short_id,
                        response_length=len(result.response_text),
                        references_count=len(result.references_map),
                        response_preview=result.response_text[:1000]  # 打印前1000字符
                    )

                    # 详细打印Stage 1的返回内容（用于debug）
                    logger.debug(
                        "stage1_response_full",
                        doc_id=doc_id,
                        doc_name=result.doc_name,
                        doc_short_id=result.doc_short_id,
                        response_text=result.response_text,  # 完整内容
                        references_map=result.references_map  # 完整引用映射
                    )

                except Exception as e:
                    logger.error(
                        "document_stage1_failed",
                        doc_id=doc_id,
                        error=str(e),
                        exc_info=True
                    )
                    # 继续处理其他文档
                    continue

            # 检查是否有成功处理的文档
            if not stage1_results:
                yield {
                    "type": "error",
                    "data": {"message": "所有文档处理失败"}
                }
                return

            logger.info(
                "stage1_completed",
                total_documents=len(document_ids),
                successful_documents=len(stage1_results)
            )

            # Stage 2: 综合答案（Markdown格式）
            logger.info(
                "starting_stage2",
                query=query[:100],
                stage1_results_count=len(stage1_results),
                total_response_length=sum(len(r.response_text) for r in stage1_results),
                doc_names=[r.doc_name for r in stage1_results]
            )

            yield {
                "type": "status",
                "message": "正在生成综合答案..."
            }

            # 调用Bedrock获取完整Markdown响应（非流式）
            markdown_response = await self._stage2_synthesize_sync(query, stage1_results)

            logger.info(
                "stage2_markdown_received",
                response_length=len(markdown_response),
                response_preview=markdown_response[:500]
            )

            # 流式输出Markdown（逐字发送，模拟流式效果）
            import asyncio
            for i in range(0, len(markdown_response), 10):  # 每次发送10个字符
                chunk = markdown_response[i:i+10]
                yield {
                    "type": "answer_delta",
                    "data": {"text": chunk}
                }
                await asyncio.sleep(0.01)  # 短暂延迟，模拟流式效果

            logger.info(
                "stage2_completed",
                answer_length=len(markdown_response)
            )

            # 提取答案中的引用并发送references事件
            references = self._extract_references_from_markdown(markdown_response, stage1_results)

            if references:
                logger.info(
                    "sending_references",
                    references_count=len(references)
                )
                yield {
                    "type": "references",
                    "data": references
                }

            # 完成
            yield {
                "type": "done",
                "data": {}
            }

            logger.info(
                "two_stage_execution_completed",
                query=query[:100],
                documents_processed=len(stage1_results)
            )

        except Exception as e:
            logger.error(
                "two_stage_execution_failed",
                query=query[:100],
                error=str(e),
                exc_info=True
            )
            yield {
                "type": "error",
                "data": {"message": str(e)}
            }

    async def _process_single_document(
        self,
        query: str,
        document_id: str
    ) -> Stage1Result:
        """
        处理单个文档（Stage 1）

        Args:
            query: 用户问题
            document_id: 文档ID

        Returns:
            Stage1Result对象
        """
        logger.info("loading_document", document_id=document_id)

        # 1. 加载文档
        doc_content = self.doc_loader.load_document(document_id)

        logger.info("processing_document", document_id=document_id)

        # 2. 处理文档（分段、标记）
        processed_doc = self.doc_processor.process(doc_content)

        logger.info(
            "calling_bedrock_stage1",
            document_id=document_id,
            content_blocks=len(processed_doc.content)
        )

        # Debug: 记录content详细信息
        content_info = []
        for block in processed_doc.content:
            if isinstance(block, dict):
                if 'text' in block:
                    content_info.append(f"text({len(block['text'])}chars)")
                elif 'image' in block:
                    content_info.append("image")
            else:
                content_info.append(f"unknown({type(block).__name__})")

        logger.info(
            'processed_doc_content_info',
            doc_short_id=processed_doc.doc_short_id,
            content_blocks=len(processed_doc.content),
            content_info=content_info[:10]  # 只显示前10个
        )

        # 3. 构建Stage 1 Prompt并调用Bedrock
        response_text = await self._call_bedrock_stage1(
            query=query,
            processed_doc=processed_doc
        )

        # 4. 返回结果
        return Stage1Result(
            doc_id=processed_doc.doc_id,
            doc_name=processed_doc.doc_name,
            doc_short_id=processed_doc.doc_short_id,
            response_text=response_text,
            references_map=processed_doc.references_map
        )

    async def _call_bedrock_stage1(
        self,
        query: str,
        processed_doc
    ) -> str:
        """
        调用Bedrock API（Stage 1）

        Args:
            query: 用户问题
            processed_doc: ProcessedDocument对象

        Returns:
            大模型的回复文本
        """
        from app.core.config import settings

        # 构建prompt文本
        prompt_text = STAGE1_PROMPT_TEMPLATE.format(
            doc_short_id=processed_doc.doc_short_id,
            query=query
        )

        # 构建完整的messages（包含prompt和图文混排content）
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt_text}] + processed_doc.content
            }
        ]

        logger.info(
            "bedrock_stage1_request_prepared",
            doc_short_id=processed_doc.doc_short_id,
            prompt_length=len(prompt_text),
            total_content_blocks=len([{"text": prompt_text}] + processed_doc.content)
        )

        try:
            # 调用Bedrock converse API（设置300秒超时）
            import asyncio
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._invoke_bedrock_sync,
                    messages,
                    temperature=0.3,
                    max_tokens=8000
                ),
                timeout=300.0  # 300秒超时
            )

            logger.info(
                "bedrock_stage1_response_received",
                doc_short_id=processed_doc.doc_short_id,
                response_length=len(response),
                response_preview=response[:500] if response else ""
            )

            return response

        except asyncio.TimeoutError:
            logger.error(
                "bedrock_stage1_timeout",
                doc_short_id=processed_doc.doc_short_id,
                timeout=300
            )
            raise Exception("Bedrock API调用超时（300秒）")

        except Exception as e:
            logger.error(
                "bedrock_stage1_call_failed",
                doc_short_id=processed_doc.doc_short_id,
                error=str(e),
                exc_info=True
            )
            raise

    def _invoke_bedrock_sync(
        self,
        messages,
        temperature: float = 0.7,
        max_tokens: int = 8000
    ) -> str:
        """
        同步调用Bedrock（辅助方法）

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            回复文本
        """
        from app.core.config import settings

        # 直接使用BedrockClient的boto_session创建runtime client
        bedrock_runtime = self.bedrock_client.boto_session.client('bedrock-runtime')

        logger.info(
            "calling_bedrock_converse_api",
            model_id=settings.generation_model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            messages_count=len(messages)
        )

        try:
            response = bedrock_runtime.converse(
                modelId=settings.generation_model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature
                }
            )

            logger.info(
                "bedrock_converse_api_success",
                input_tokens=response.get('usage', {}).get('inputTokens', 0),
                output_tokens=response.get('usage', {}).get('outputTokens', 0)
            )

            # 提取回复文本
            output_message = response['output']['message']
            text = output_message['content'][0]['text']

            return text

        except Exception as e:
            logger.error(
                "bedrock_converse_api_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    async def _stage2_synthesize_sync(
        self,
        query: str,
        stage1_results: List[Stage1Result]
    ) -> str:
        """
        Stage 2: 综合所有文档的理解结果，生成Markdown格式答案（非流式）

        Args:
            query: 用户问题
            stage1_results: 所有Stage 1的结果

        Returns:
            完整的Markdown响应文本
        """
        # 1. 构建Stage 2 Prompt
        prompt = self._build_stage2_prompt(query, stage1_results)

        # 2. 调用Bedrock同步API
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        try:
            # 使用同步API获取完整响应（设置300秒超时，Stage 2可能需要更长时间）
            import asyncio
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._invoke_bedrock_sync,
                    messages,
                    temperature=0.7,
                    max_tokens=8000
                ),
                timeout=300.0  # 300秒超时
            )

            logger.info(
                "bedrock_stage2_sync_completed",
                response_length=len(response),
                response_preview=response[:500] if response else ""
            )

            return response

        except asyncio.TimeoutError:
            logger.error(
                "bedrock_stage2_timeout",
                timeout=300
            )
            raise Exception("Bedrock Stage 2调用超时（300秒）")

        except Exception as e:
            logger.error(
                "bedrock_stage2_sync_failed",
                error=str(e),
                exc_info=True
            )
            raise

    def _parse_llm_references(
        self,
        llm_references: List[Dict],
        stage1_results: List[Stage1Result]
    ) -> List:
        """
        解析LLM返回的references列表

        Args:
            llm_references: LLM返回的引用列表
            stage1_results: Stage 1结果列表

        Returns:
            Reference对象列表
        """
        from app.services.reference_extractor import Reference

        # 打印详细debug信息
        logger.info(
            "parsing_llm_references_start",
            llm_references_count=len(llm_references),
            llm_references=llm_references,  # 打印原始数据
            available_doc_short_ids=[r.doc_short_id for r in stage1_results]
        )

        references = []

        for idx, ref_item in enumerate(llm_references, 1):
            try:
                chunk_id = ref_item.get("chunk_id", "")
                chunk_type = ref_item.get("chunk_type", "text")
                chunk_content = ref_item.get("chunk_content", "")

                logger.debug(
                    "processing_llm_reference",
                    index=idx,
                    chunk_id=chunk_id,
                    chunk_type=chunk_type,
                    chunk_content_length=len(chunk_content)
                )

                # 从chunk_id中提取doc_short_id
                # 格式：[DOC-abc12345-PARA-5] 或 [DOC-abc12345-IMAGE-2]
                chunk_id_clean = chunk_id.strip("[]").strip()

                # 查找对应的stage1_result
                doc_short_id = None
                doc_id = None
                doc_name = None
                target_result = None

                if chunk_id_clean.startswith("DOC-"):
                    # 使用正则表达式精确提取doc_short_id
                    # 格式：DOC-{doc_short_id}-(PARA|IMAGE)-{number}
                    # 例如：DOC-doc-3931-PARA-13 或 DOC-abc12345-IMAGE-2
                    import re
                    match = re.match(r'^DOC-(.+?)-(PARA|IMAGE)-(\d+)$', chunk_id_clean, re.IGNORECASE)

                    if match:
                        doc_short_id = match.group(1)  # 提取doc_short_id（可能包含连字符）

                        logger.debug(
                            "extracted_doc_short_id",
                            chunk_id=chunk_id,
                            chunk_id_clean=chunk_id_clean,
                            doc_short_id=doc_short_id,
                            chunk_type=match.group(2),
                            chunk_number=match.group(3)
                        )

                        # 从stage1_results中找到对应的文档（不区分大小写）
                        for result in stage1_results:
                            if result.doc_short_id.lower() == doc_short_id.lower():
                                doc_id = result.doc_id
                                doc_name = result.doc_name
                                target_result = result
                                logger.debug(
                                    "doc_matched",
                                    chunk_id=chunk_id,
                                    doc_short_id=doc_short_id,
                                    matched_doc_id=doc_id
                                )
                                break
                    else:
                        logger.warning(
                            "invalid_chunk_id_format",
                            chunk_id=chunk_id,
                            chunk_id_clean=chunk_id_clean,
                            expected_format="DOC-{doc_short_id}-(PARA|IMAGE)-{number}"
                        )

                if not doc_id:
                    logger.warning(
                        "llm_reference_doc_not_found",
                        chunk_id=chunk_id,
                        chunk_id_clean=chunk_id_clean,
                        extracted_doc_short_id=doc_short_id,
                        available_doc_short_ids=[r.doc_short_id for r in stage1_results]
                    )
                    continue

                # 尝试从references_map中获取真实内容
                real_content = chunk_content
                if target_result and chunk_id_clean in target_result.references_map:
                    real_content = target_result.references_map[chunk_id_clean]
                    logger.debug(
                        "found_in_references_map",
                        chunk_id=chunk_id_clean,
                        content_length=len(real_content) if isinstance(real_content, str) else 0
                    )
                elif target_result:
                    logger.warning(
                        "chunk_id_not_in_references_map",
                        chunk_id=chunk_id_clean,
                        available_refs=list(target_result.references_map.keys())[:5]  # 只打印前5个
                    )

                # 构建image_url
                image_url = None
                if chunk_type == "image":
                    # chunk_content可能是image_url或文件名
                    if chunk_content.startswith("http") or chunk_content.startswith("/api/"):
                        image_url = chunk_content
                    else:
                        # real_content应该是图片文件名
                        image_url = f"/api/v1/documents/{doc_id}/images/{real_content}"
                        logger.debug(
                            "constructed_image_url",
                            chunk_id=chunk_id_clean,
                            image_url=image_url
                        )

                ref = Reference(
                    ref_id=chunk_id_clean,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    chunk_type=chunk_type,
                    content=real_content if chunk_type == "text" else None,
                    image_url=image_url
                )
                references.append(ref)

                logger.debug(
                    "reference_added",
                    ref_id=chunk_id_clean,
                    doc_id=doc_id,
                    chunk_type=chunk_type
                )

            except Exception as e:
                logger.error(
                    "parse_llm_reference_failed",
                    index=idx,
                    ref_item=ref_item,
                    error=str(e),
                    exc_info=True
                )
                continue

        logger.info(
            "llm_references_parsed",
            input_count=len(llm_references),
            output_count=len(references),
            success_rate=f"{len(references)}/{len(llm_references)}"
        )

        return references

    def _build_fallback_references(self, stage1_results: List[Stage1Result]) -> List:
        """
        降级方案：从stage1_results中构建基础引用列表
        当LLM没有在答案中生成引用标记时使用

        Args:
            stage1_results: Stage 1结果列表

        Returns:
            Reference对象列表
        """
        from app.services.reference_extractor import Reference

        references = []

        for result in stage1_results:
            # 从每个文档的references_map中取前3个引用
            ref_items = list(result.references_map.items())[:3]

            for ref_id, content in ref_items:
                # 判断类型（PARA或IMAGE）
                chunk_type = "text" if "-PARA-" in ref_id else "image"

                # 构建image_url
                image_url = None
                if chunk_type == "image":
                    # content是图片文件名，构建URL
                    image_url = f"/api/v1/documents/{result.doc_id}/images/{content}"

                references.append(Reference(
                    ref_id=ref_id,
                    doc_id=result.doc_id,
                    doc_name=result.doc_name,
                    chunk_type=chunk_type,
                    content=content if chunk_type == "text" else None,
                    image_url=image_url
                ))

        logger.info(
            "fallback_references_built",
            count=len(references)
        )

        return references

    def _extract_references_from_markdown(
        self,
        markdown_text: str,
        stage1_results: List[Stage1Result]
    ) -> List[Dict]:
        """
        从Markdown答案中提取引用标记，并构建完整的引用列表

        Args:
            markdown_text: Stage 2生成的Markdown答案
            stage1_results: Stage 1结果列表

        Returns:
            引用对象列表，格式符合前端CitationItem的要求
        """
        import re

        # 使用正则表达式提取所有的 [DOC-xxx-PARA-X] 和 [DOC-xxx-IMAGE-X] 标记
        pattern = r'\[DOC-[^\]]+\]'
        matches = re.findall(pattern, markdown_text)

        # 去重
        unique_refs = list(set(matches))

        logger.info(
            "extracted_references_from_markdown",
            total_matches=len(matches),
            unique_refs=len(unique_refs),
            refs_preview=unique_refs[:10]
        )

        references = []

        for ref_text in unique_refs:
            # 去掉方括号
            ref_id = ref_text.strip('[]')

            # 查找对应的stage1_result和引用内容
            found = False
            for result in stage1_results:
                if ref_id in result.references_map:
                    content = result.references_map[ref_id]

                    # 判断类型（PARA或IMAGE）
                    chunk_type = "text" if "-PARA-" in ref_id else "image"

                    # 构建引用对象
                    ref_obj = {
                        "ref_id": ref_id,
                        "doc_id": result.doc_id,
                        "doc_name": result.doc_name,
                        "chunk_type": chunk_type,
                        "content": content if chunk_type == "text" else None,
                        "image_url": None
                    }

                    # 如果是图片，构建image_url
                    if chunk_type == "image":
                        # content是图片文件名
                        ref_obj["image_url"] = f"/api/v1/documents/{result.doc_id}/images/{content}"
                        ref_obj["content"] = content  # 保留文件名作为content

                    references.append(ref_obj)
                    found = True

                    logger.debug(
                        "reference_matched",
                        ref_id=ref_id,
                        doc_id=result.doc_id,
                        chunk_type=chunk_type
                    )
                    break

            if not found:
                logger.warning(
                    "reference_not_found_in_stage1_results",
                    ref_id=ref_id,
                    available_docs=[r.doc_short_id for r in stage1_results]
                )

        logger.info(
            "references_extraction_completed",
            total_extracted=len(references)
        )

        return references

    def _build_stage2_prompt(self, query: str, stage1_results: List[Stage1Result]) -> str:
        """
        构建Stage 2 Prompt

        Args:
            query: 用户问题
            stage1_results: Stage 1结果列表

        Returns:
            完整的prompt文本
        """
        # 格式化所有stage1_results
        formatted_responses = []
        for idx, result in enumerate(stage1_results, 1):
            formatted_responses.append(f"""
=== 文档 {idx}: {result.doc_name} ===

{result.response_text}
""")

        all_responses_text = "\n\n".join(formatted_responses)

        # 填充模板
        prompt = STAGE2_PROMPT_TEMPLATE.format(
            doc_count=len(stage1_results),
            all_stage1_responses=all_responses_text,
            query=query
        )

        # 打印Stage 2的完整prompt（用于debug）
        logger.debug(
            "stage2_prompt_built",
            prompt_length=len(prompt),
            prompt_preview=prompt[:2000],  # 前2000字符
            full_prompt=prompt  # 完整prompt
        )

        return prompt
