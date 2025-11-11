"""
查询服务
实现Hybrid Search和Multi-Agent问答流程
"""
import asyncio
import uuid
from typing import List, Dict, AsyncGenerator
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import KnowledgeBaseNotFoundError
from app.models.database import KnowledgeBase, Document, Chunk
from app.utils.opensearch_client import opensearch_client
from app.utils.bedrock_client import bedrock_client
from app.agents.sub_agent import create_sub_agent, invoke_sub_agent
from app.agents.main_agent import create_main_agent, invoke_main_agent_stream

logger = get_logger(__name__)


class QueryService:
    """查询服务"""

    # 检索参数
    TOP_K = 20  # 检索的chunk数量
    MAX_DOCUMENTS = 10  # 最多读取的文档数
    MAX_CONCURRENT_AGENTS = 5  # 最大并发Agent数

    @staticmethod
    async def execute_query_stream(
        db: Session,
        kb_id: str,
        query_text: str
    ) -> AsyncGenerator[Dict, None]:
        """
        执行查询并流式返回结果

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            query_text: 用户问题

        Yields:
            流式事件
        """
        query_id = str(uuid.uuid4())

        logger.info(
            "start_query_execution",
            query_id=query_id,
            kb_id=kb_id,
            query=query_text[:100]
        )

        try:
            # 验证知识库存在
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                raise KnowledgeBaseNotFoundError(kb_id)

            # Step 1: Query Rewrite（可选，暂时简化）
            yield {
                "type": "status",
                "message": "正在优化查询..."
            }

            # Step 2: Hybrid Search
            yield {
                "type": "status",
                "message": "正在检索相关文档..."
            }

            search_results = await QueryService._hybrid_search(
                db=db,
                kb=kb,
                query_text=query_text
            )

            if not search_results:
                yield {
                    "type": "status",
                    "message": "未找到相关文档"
                }
                yield {
                    "type": "text_delta",
                    "content": "抱歉，在知识库中未找到与您问题相关的内容。"
                }
                yield {
                    "type": "complete",
                    "query_id": query_id,
                    "total_tokens": 0
                }
                return

            # 按文档聚合chunks
            doc_chunks = QueryService._group_chunks_by_document(search_results)

            yield {
                "type": "retrieved_documents",
                "document_ids": list(doc_chunks.keys()),
                "document_count": len(doc_chunks),
                "chunk_count": len(search_results)
            }

            # Step 3: 调用Sub-Agents读取文档
            yield {
                "type": "status",
                "message": f"正在深度阅读 {len(doc_chunks)} 个文档..."
            }

            sub_agent_results = await QueryService._invoke_sub_agents(
                db=db,
                query_text=query_text,
                doc_chunks=doc_chunks
            )

            # 发送citation事件（相关chunks）
            for doc_id, doc_data in doc_chunks.items():
                doc = db.query(Document).filter(Document.id == doc_id).first()
                doc_name = doc.filename if doc else "Unknown"

                for chunk_data in doc_data["chunks"][:3]:  # 每个文档最多3个引用
                    # 获取完整chunk信息
                    chunk_id = chunk_data.get("chunk_id")
                    if chunk_id:
                        chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
                        if chunk:
                            citation = {
                                "chunk_id": chunk.id,
                                "chunk_type": chunk.chunk_type,
                                "document_id": doc_id,
                                "document_name": doc_name,
                                "chunk_index": chunk.chunk_index
                            }

                            if chunk.chunk_type == "text":
                                citation["content"] = chunk.content[:200]  # 前200字
                            else:  # image
                                citation["image_description"] = chunk.image_description
                                citation["image_url"] = f"/api/v1/chunks/{chunk.id}/image"

                            yield {
                                "type": "citation",
                                **citation
                            }

            # Step 4: 调用Main-Agent综合答案
            yield {
                "type": "status",
                "message": "正在生成答案..."
            }

            main_agent = create_main_agent()

            async for event in invoke_main_agent_stream(
                agent=main_agent,
                query=query_text,
                sub_agent_results=sub_agent_results
            ):
                # 修改事件类型以符合docs规范
                if event.get("type") == "text_delta":
                    # 将text_delta改为chunk
                    yield {
                        "type": "chunk",
                        "content": event.get("content", "")
                    }
                elif event.get("type") == "complete":
                    # 发送done事件
                    yield {
                        "type": "done",
                        "query_id": query_id
                    }
                else:
                    yield event

            logger.info(
                "query_execution_completed",
                query_id=query_id
            )

        except Exception as e:
            logger.error(
                "query_execution_failed",
                query_id=query_id,
                error=str(e),
                exc_info=True
            )

            yield {
                "type": "error",
                "message": f"查询执行失败: {str(e)}"
            }

    @staticmethod
    async def _hybrid_search(
        db: Session,
        kb: KnowledgeBase,
        query_text: str
    ) -> List[Dict]:
        """
        混合检索（向量 + BM25）

        Args:
            db: 数据库会话
            kb: 知识库对象
            query_text: 查询文本

        Returns:
            检索结果列表
        """
        logger.info("start_hybrid_search", kb_id=kb.id)

        index_name = kb.opensearch_index_name

        # 生成查询向量
        query_embedding = bedrock_client.generate_embedding(query_text)

        # 执行混合检索
        results = opensearch_client.hybrid_search(
            index_name=index_name,
            query_text=query_text,
            query_vector=query_embedding,
            top_k=QueryService.TOP_K
        )

        logger.info(
            "hybrid_search_completed",
            kb_id=kb.id,
            results_count=len(results)
        )

        return results

    @staticmethod
    def _group_chunks_by_document(chunks: List[Dict]) -> Dict[str, Dict]:
        """
        按文档聚合chunks

        Args:
            chunks: chunk列表（来自OpenSearch，格式：{'id': '...', 'score': '...', 'source': {...}}）

        Returns:
            按document_id分组的字典
        """
        doc_chunks = {}

        for chunk in chunks:
            # OpenSearch返回格式：document_id在source里面
            source = chunk.get("source", {})
            doc_id = source.get("document_id")

            # 跳过没有document_id的chunk
            if not doc_id:
                logger.warning("chunk_missing_document_id", chunk_id=chunk.get("id"))
                continue

            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = {
                    "document_id": doc_id,
                    "chunks": []
                }

            # 保存完整的chunk信息（包括source）
            doc_chunks[doc_id]["chunks"].append(chunk)

        return doc_chunks

    @staticmethod
    async def _invoke_sub_agents(
        db: Session,
        query_text: str,
        doc_chunks: Dict[str, Dict]
    ) -> List[Dict]:
        """
        并发调用Sub-Agents

        Args:
            db: 数据库会话
            query_text: 查询文本
            doc_chunks: 按文档分组的chunks

        Returns:
            Sub-Agent结果列表
        """
        logger.info(
            "start_sub_agents",
            document_count=len(doc_chunks)
        )

        # 限制文档数量
        doc_ids = list(doc_chunks.keys())[:QueryService.MAX_DOCUMENTS]

        # 创建任务列表
        tasks = []

        for doc_id in doc_ids:
            task = QueryService._process_single_document(
                db=db,
                query_text=query_text,
                document_id=doc_id,
                chunks=doc_chunks[doc_id]["chunks"]
            )
            tasks.append(task)

        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(QueryService.MAX_CONCURRENT_AGENTS)

        async def bounded_task(task):
            async with semaphore:
                return await task

        # 并发执行
        results = await asyncio.gather(*[bounded_task(task) for task in tasks])

        logger.info(
            "sub_agents_completed",
            results_count=len(results)
        )

        return results

    @staticmethod
    async def _process_single_document(
        db: Session,
        query_text: str,
        document_id: str,
        chunks: List[Dict]
    ) -> Dict:
        """
        处理单个文档

        Args:
            db: 数据库会话
            query_text: 查询文本
            document_id: 文档ID
            chunks: chunk列表

        Returns:
            Sub-Agent结果
        """
        logger.info("processing_document", document_id=document_id)

        try:
            # 获取文档信息
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return {
                    "document_id": document_id,
                    "document_name": "Unknown",
                    "answer": "文档不存在",
                    "has_relevant_info": False,
                    "confidence": 0.0
                }

            # 下载Markdown内容
            markdown_content = await QueryService._get_document_content(doc)

            # 获取图片信息
            images = QueryService._get_document_images(db, document_id)

            # 构建相关上下文（从chunks提取）
            context = "\n\n".join([
                chunk.get("content", "") for chunk in chunks[:5]
            ])

            # 创建Sub-Agent
            sub_agent = create_sub_agent(
                document_id=document_id,
                document_name=doc.filename,
                markdown_content=markdown_content,
                images=images,
                relevant_context=context
            )

            # 调用Sub-Agent
            result = await invoke_sub_agent(
                agent=sub_agent,
                query=query_text,
                document_id=document_id,
                document_name=doc.filename
            )

            return result

        except Exception as e:
            logger.error(
                "process_document_failed",
                document_id=document_id,
                error=str(e)
            )

            return {
                "document_id": document_id,
                "document_name": "Unknown",
                "answer": f"处理失败: {str(e)}",
                "has_relevant_info": False,
                "confidence": 0.0
            }

    @staticmethod
    async def _get_document_content(doc: Document) -> str:
        """
        获取文档的Markdown内容（从本地文件系统）

        Args:
            doc: 文档对象

        Returns:
            Markdown内容
        """
        if doc.local_markdown_path:
            try:
                with open(doc.local_markdown_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(
                    "read_markdown_failed",
                    document_id=doc.id,
                    path=doc.local_markdown_path,
                    error=str(e)
                )

        return ""

    @staticmethod
    def _get_document_images(db: Session, document_id: str) -> List[Dict]:
        """
        获取文档的图片信息

        Args:
            db: 数据库会话
            document_id: 文档ID

        Returns:
            图片信息列表
        """
        image_chunks = db.query(Chunk).filter(
            Chunk.document_id == document_id,
            Chunk.chunk_type == "image"
        ).order_by(Chunk.chunk_index).all()

        images = []
        for chunk in image_chunks:
            images.append({
                "filename": chunk.image_filename,
                "description": chunk.image_description,
                "type": chunk.image_type or "other"
            })

        return images


    @staticmethod
    async def execute_query_two_stage(
        db: Session,
        kb_id: str,
        query_text: str
    ) -> AsyncGenerator[Dict, None]:
        """
        使用TwoStageExecutor执行查询并流式返回结果

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            query_text: 用户问题

        Yields:
            流式事件
        """
        query_id = str(uuid.uuid4())

        logger.info(
            "start_two_stage_query",
            query_id=query_id,
            kb_id=kb_id,
            query=query_text[:100]
        )

        try:
            # 验证知识库存在
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                raise KnowledgeBaseNotFoundError(kb_id)

            # Step 1: 混合检索
            yield {
                "type": "status",
                "message": "正在检索相关文档..."
            }

            search_results = await QueryService._hybrid_search(
                db=db,
                kb=kb,
                query_text=query_text
            )

            if not search_results:
                yield {
                    "type": "status",
                    "message": "未找到相关文档"
                }
                yield {
                    "type": "answer_delta",
                    "data": {"text": "抱歉，在知识库中未找到与您问题相关的内容。"}
                }
                yield {
                    "type": "done",
                    "data": {"query_id": query_id, "tokens": {"total_tokens": 0}}
                }
                return

            # Step 2: 提取唯一的Document ID列表
            doc_chunks = QueryService._group_chunks_by_document(search_results)
            document_ids = list(doc_chunks.keys())[:QueryService.MAX_DOCUMENTS]

            logger.info(
                "documents_retrieved",
                query_id=query_id,
                document_count=len(document_ids)
            )

            yield {
                "type": "retrieved_documents",
                "document_ids": document_ids,
                "document_count": len(document_ids)
            }

            # Step 3: 使用TwoStageExecutor处理
            from app.services.agentic_robot import TwoStageExecutor

            executor = TwoStageExecutor(
                db_session=db,
                bedrock_client=bedrock_client
            )

            async for event in executor.execute_streaming(
                query=query_text,
                document_ids=document_ids
            ):
                yield event

            logger.info(
                "two_stage_query_completed",
                query_id=query_id
            )

        except Exception as e:
            logger.error(
                "two_stage_query_failed",
                query_id=query_id,
                error=str(e),
                exc_info=True
            )

            yield {
                "type": "error",
                "data": {"message": f"查询执行失败: {str(e)}"}
            }


# 全局实例
query_service = QueryService()
