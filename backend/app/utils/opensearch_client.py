"""
AWS OpenSearch客户端工具类
用于向量存储和混合检索
"""
from typing import List, Dict, Any, Optional
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import OpenSearchConnectionError, VectorizationError

logger = get_logger(__name__)


class OpenSearchClient:
    """OpenSearch客户端封装"""

    def __init__(self):
        """初始化OpenSearch客户端"""
        try:
            # 创建AWS认证
            credentials = boto3.Session(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            ).get_credentials()

            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                settings.aws_region,
                'aoss',  # Amazon OpenSearch Serverless
                session_token=credentials.token
            )

            # 创建OpenSearch客户端
            self.client = OpenSearch(
                hosts=[{'host': settings.opensearch_endpoint.replace('https://', ''), 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )

            logger.info("opensearch_client_initialized", endpoint=settings.opensearch_endpoint)

        except Exception as e:
            logger.error("opensearch_init_failed", error=str(e))
            raise OpenSearchConnectionError({"error": str(e)})

    def create_index(self, index_name: str, embedding_dimension: int = 1024) -> bool:
        """
        创建向量索引

        Args:
            index_name: 索引名称
            embedding_dimension: 向量维度（Titan Embeddings V2: 1024）

        Returns:
            是否创建成功
        """
        try:
            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": True,
                        "knn.algo_param.ef_search": 512
                    }
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "kb_id": {"type": "keyword"},
                        "chunk_type": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "content": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "content_with_context": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": embedding_dimension,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 512,
                                    "m": 16
                                }
                            }
                        },
                        "created_at": {"type": "date"}
                    }
                }
            }

            response = self.client.indices.create(index=index_name, body=index_body)
            logger.info("opensearch_index_created", index_name=index_name)
            return response.get('acknowledged', False)

        except Exception as e:
            logger.error("opensearch_create_index_failed", index_name=index_name, error=str(e))
            raise OpenSearchConnectionError({"error": str(e), "index_name": index_name})

    def delete_index(self, index_name: str) -> bool:
        """
        删除索引

        Args:
            index_name: 索引名称

        Returns:
            是否删除成功
        """
        try:
            if self.index_exists(index_name):
                response = self.client.indices.delete(index=index_name)
                logger.info("opensearch_index_deleted", index_name=index_name)
                return response.get('acknowledged', False)
            return True

        except Exception as e:
            logger.error("opensearch_delete_index_failed", index_name=index_name, error=str(e))
            return False

    def index_exists(self, index_name: str) -> bool:
        """
        检查索引是否存在

        Args:
            index_name: 索引名称

        Returns:
            索引是否存在
        """
        try:
            return self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error("opensearch_check_index_failed", index_name=index_name, error=str(e))
            return False

    def index_document(
        self,
        index_name: str,
        doc_id: str,
        document: Dict[str, Any]
    ) -> bool:
        """
        索引单个文档

        Args:
            index_name: 索引名称
            doc_id: 文档ID
            document: 文档内容

        Returns:
            是否索引成功
        """
        try:
            response = self.client.index(
                index=index_name,
                id=doc_id,
                body=document,
                refresh=True
            )
            logger.debug("document_indexed", index_name=index_name, doc_id=doc_id)
            return response.get('result') in ['created', 'updated']

        except Exception as e:
            logger.error("opensearch_index_doc_failed", index_name=index_name, doc_id=doc_id, error=str(e))
            raise VectorizationError({"error": str(e), "doc_id": doc_id})

    def bulk_index(
        self,
        index_name: str,
        documents: List[Dict[str, Any]],
        id_field: str = "chunk_id"
    ) -> int:
        """
        批量索引文档

        Args:
            index_name: 索引名称
            documents: 文档列表
            id_field: 用作文档ID的字段名

        Returns:
            成功索引的文档数量
        """
        try:
            from opensearchpy.helpers import bulk

            actions = []
            for doc in documents:
                action = {
                    "_index": index_name,
                    "_id": doc.get(id_field),
                    "_source": doc
                }
                actions.append(action)

            success, failed = bulk(self.client, actions, refresh=True)
            logger.info("bulk_index_completed", index_name=index_name, success=success, failed=failed)
            return success

        except Exception as e:
            logger.error("opensearch_bulk_index_failed", index_name=index_name, error=str(e))
            raise VectorizationError({"error": str(e), "count": len(documents)})

    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """
        删除文档

        Args:
            index_name: 索引名称
            doc_id: 文档ID

        Returns:
            是否删除成功
        """
        try:
            response = self.client.delete(
                index=index_name,
                id=doc_id,
                refresh=True
            )
            logger.debug("document_deleted", index_name=index_name, doc_id=doc_id)
            return response.get('result') == 'deleted'

        except Exception as e:
            logger.error("opensearch_delete_doc_failed", index_name=index_name, doc_id=doc_id, error=str(e))
            return False

    def delete_by_query(self, index_name: str, query: Dict[str, Any]) -> int:
        """
        按查询删除文档

        Args:
            index_name: 索引名称
            query: 删除查询

        Returns:
            删除的文档数量
        """
        try:
            response = self.client.delete_by_query(
                index=index_name,
                body={"query": query},
                refresh=True
            )
            deleted = response.get('deleted', 0)
            logger.info("documents_deleted_by_query", index_name=index_name, deleted=deleted)
            return deleted

        except Exception as e:
            logger.error("opensearch_delete_by_query_failed", index_name=index_name, error=str(e))
            return 0

    def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索（kNN）

        Args:
            index_name: 索引名称
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            检索结果列表
        """
        try:
            query_body = {
                "size": top_k,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_vector,
                            "k": top_k
                        }
                    }
                }
            }

            # 添加过滤条件
            if filters:
                query_body["query"]["knn"]["embedding"]["filter"] = filters

            response = self.client.search(index=index_name, body=query_body)

            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                })

            logger.debug("vector_search_completed", index_name=index_name, results=len(results))
            return results

        except Exception as e:
            logger.error("opensearch_vector_search_failed", index_name=index_name, error=str(e))
            return []

    def keyword_search(
        self,
        index_name: str,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        关键词检索（BM25）

        Args:
            index_name: 索引名称
            query_text: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            检索结果列表
        """
        try:
            query_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": ["content^2", "content_with_context"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                }
            }

            # 添加过滤条件
            if filters:
                query_body["query"]["bool"]["filter"] = filters

            response = self.client.search(index=index_name, body=query_body)

            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                })

            logger.debug("keyword_search_completed", index_name=index_name, results=len(results))
            return results

        except Exception as e:
            logger.error("opensearch_keyword_search_failed", index_name=index_name, error=str(e))
            return []

    def hybrid_search(
        self,
        index_name: str,
        query_text: str,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索（向量 + BM25）
        使用RRF (Reciprocal Rank Fusion)合并结果

        Args:
            index_name: 索引名称
            query_text: 查询文本
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            检索结果列表
        """
        # 1. 向量检索
        vector_results = self.vector_search(index_name, query_vector, top_k, filters)

        # 2. 关键词检索
        keyword_results = self.keyword_search(index_name, query_text, top_k, filters)

        # 3. RRF合并
        merged = self._reciprocal_rank_fusion(
            [vector_results, keyword_results],
            k=60
        )

        return merged[:top_k]

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion算法合并多个检索结果

        Args:
            result_lists: 多个检索结果列表
            k: RRF参数

        Returns:
            合并后的结果列表
        """
        rrf_scores = {}

        for results in result_lists:
            for rank, result in enumerate(results, start=1):
                doc_id = result['id']
                score = 1.0 / (k + rank)

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = {
                        'id': doc_id,
                        'score': 0.0,
                        'source': result['source']
                    }

                rrf_scores[doc_id]['score'] += score

        # 按分数排序
        merged = sorted(rrf_scores.values(), key=lambda x: x['score'], reverse=True)
        return merged


# 全局OpenSearch客户端实例
opensearch_client = OpenSearchClient()
