"""
Pydantic数据模型
用于API请求和响应的数据验证
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ============ 基础响应模型 ============

class BaseResponse(BaseModel):
    """基础响应模型"""
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """错误响应"""
    error_code: str
    message: str
    details: Dict[str, Any] = {}


class PaginationMeta(BaseModel):
    """分页元信息"""
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


# ============ 知识库相关模型 ============

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="描述信息")
    s3_bucket: str = Field(..., description="S3桶名")
    s3_prefix: str = Field(..., description="S3路径前缀，必须以/结尾")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "产品PRD知识库",
                "description": "包含产品迭代的所有PRD文档",
                "s3_bucket": "my-bucket",
                "s3_prefix": "prds/product-a/"
            }
        }
    )


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class KnowledgeBaseResponse(BaseResponse):
    """知识库响应"""
    id: str
    name: str
    description: Optional[str]
    s3_bucket: str
    s3_prefix: str
    opensearch_collection_id: Optional[str]
    opensearch_index_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: List[KnowledgeBaseResponse]
    meta: PaginationMeta


class KnowledgeBaseStats(BaseModel):
    """知识库统计信息"""
    document_count: int = 0
    chunk_count: int = 0
    total_size_bytes: int = 0


class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    """知识库详情响应（包含统计信息）"""
    stats: KnowledgeBaseStats


# ============ 文档相关模型 ============

class DocumentResponse(BaseResponse):
    """文档响应"""
    id: str
    kb_id: str
    filename: str
    s3_key: str
    s3_key_markdown: Optional[str]
    file_size: Optional[int]
    page_count: Optional[int]
    status: str  # uploaded | processing | completed | failed
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: List[DocumentResponse]
    meta: PaginationMeta


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应（包含统计信息）"""
    stats: Dict[str, int]


class DocumentCreate(BaseModel):
    """文档创建请求（内部使用）"""
    kb_id: str
    filename: str
    file_size: int
    s3_key: str


class DocumentUpdate(BaseModel):
    """文档更新请求"""
    status: Optional[str] = None
    s3_key_markdown: Optional[str] = None
    local_markdown_path: Optional[str] = None
    error_message: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    s3_key: str
    file_size: int
    message: str = "文档上传成功"


# ============ Chunk相关模型 ============

class ChunkResponse(BaseResponse):
    """Chunk响应"""
    id: str
    document_id: str
    kb_id: str
    chunk_type: str  # text | image
    chunk_index: int
    content: Optional[str]  # 文本chunk
    image_filename: Optional[str]  # 图片chunk
    image_description: Optional[str]  # 图片描述
    image_type: Optional[str]  # 图片类型
    token_count: Optional[int]
    created_at: datetime


# ============ 同步任务相关模型 ============

class SyncTaskCreate(BaseModel):
    """创建同步任务请求"""
    kb_id: str = Field(..., description="知识库ID")
    task_type: str = Field(..., description="任务类型: full_sync | incremental | delete")
    document_ids: Optional[List[str]] = Field(None, description="文档ID列表（增量同步时使用）")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
                "task_type": "full_sync",
                "document_ids": []
            }
        }
    )


class SyncTaskResponse(BaseResponse):
    """同步任务响应"""
    id: str
    kb_id: str
    task_type: str
    status: str  # pending | running | completed | failed | partial_success
    progress: int  # 0-100
    current_step: Optional[str]
    total_documents: int
    processed_documents: int
    failed_documents: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class SyncTaskListResponse(BaseModel):
    """同步任务列表响应"""
    items: List[SyncTaskResponse]
    meta: PaginationMeta


# ============ 查询相关模型 ============

class QueryRequest(BaseModel):
    """查询请求"""
    kb_id: str = Field(..., description="知识库ID")
    query_text: str = Field(..., min_length=1, max_length=1000, description="用户问题")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kb_id": "kb-550e8400-e29b-41d4-a716-446655440000",
                "query_text": "登录注册模块的演进历史是怎样的？"
            }
        }
    )


class CitationItem(BaseModel):
    """引用项"""
    chunk_id: str
    chunk_type: str  # text | image
    document_id: str
    document_name: str
    content: Optional[str]  # 文本内容或图片描述
    chunk_index: int
    image_url: Optional[str]  # 图片URL（如果是图片chunk）


# ============ 流式输出事件模型 ============

class StreamEvent(BaseModel):
    """流式输出事件基类"""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusEvent(StreamEvent):
    """状态更新事件"""
    type: str = "status"
    message: str


class TextDeltaEvent(StreamEvent):
    """文本增量事件"""
    type: str = "text_delta"
    text: str


class CompleteEvent(StreamEvent):
    """完成事件"""
    type: str = "complete"
    citations: List[CitationItem]
    metrics: Dict[str, int]


class ErrorEvent(StreamEvent):
    """错误事件"""
    type: str = "error"
    error_code: str
    message: str
    details: Dict[str, Any] = {}
