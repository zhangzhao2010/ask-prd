"""
查询服务
实现Hybrid Search和Multi-Agent问答流程
"""
import uuid
from typing import List, Dict, AsyncGenerator
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.errors import KnowledgeBaseNotFoundError
from app.models.database import KnowledgeBase
from app.utils.opensearch_client import opensearch_client
from app.utils.bedrock_client import bedrock_client

logger = get_logger(__name__)


class QueryService:
    """查询服务"""

    # 检索参数
    TOP_K = 20  # 检索的chunk数量
    MAX_DOCUMENTS = 10  # 最多读取的文档数

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
    async def execute_query_two_stage(
        db: Session,
        kb_id: str,
        query_text: str,
        user_id: int
    ) -> AsyncGenerator[Dict, None]:
        """
        使用TwoStageExecutor执行查询并流式返回结果

        Args:
            db: 数据库会话
            kb_id: 知识库ID
            query_text: 用户问题
            user_id: 用户ID（用于记录查询历史）

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
