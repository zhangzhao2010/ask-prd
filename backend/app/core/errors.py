"""
自定义异常类
基于docs/error-handling.md设计
"""
from typing import Optional, Dict, Any


class ASKPRDException(Exception):
    """基础异常类"""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


# ============ 知识库相关异常 (1xxx) ============

class KnowledgeBaseNotFoundError(ASKPRDException):
    """知识库不存在"""

    def __init__(self, kb_id: str):
        super().__init__(
            error_code="1001",
            message=f"知识库不存在: {kb_id}",
            details={"kb_id": kb_id},
            status_code=404
        )


class KnowledgeBaseAlreadyExistsError(ASKPRDException):
    """知识库已存在"""

    def __init__(self, name: str):
        super().__init__(
            error_code="1002",
            message=f"知识库名称已存在: {name}",
            details={"name": name},
            status_code=409
        )


class OpenSearchConnectionError(ASKPRDException):
    """OpenSearch连接失败"""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            error_code="1010",
            message="OpenSearch服务连接失败",
            details=details,
            status_code=503
        )


# ============ 文档相关异常 (2xxx) ============

class DocumentNotFoundError(ASKPRDException):
    """文档不存在"""

    def __init__(self, doc_id: str):
        super().__init__(
            error_code="2001",
            message=f"文档不存在: {doc_id}",
            details={"document_id": doc_id},
            status_code=404
        )


class FileUploadError(ASKPRDException):
    """文件上传失败"""

    def __init__(self, filename: str, reason: str):
        super().__init__(
            error_code="2010",
            message=f"文件上传失败: {filename}",
            details={"filename": filename, "reason": reason},
            status_code=400
        )


class S3UploadError(ASKPRDException):
    """S3上传失败"""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            error_code="2011",
            message="S3上传失败",
            details=details or {},
            status_code=503
        )


# ============ 同步任务相关异常 (3xxx) ============

class PDFConversionError(ASKPRDException):
    """PDF转换失败"""

    def __init__(self, doc_id: str, reason: str):
        super().__init__(
            error_code="3010",
            message=f"PDF转换失败: {doc_id}",
            details={"document_id": doc_id, "reason": reason},
            status_code=500
        )


class VectorizationError(ASKPRDException):
    """向量化失败"""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            error_code="3020",
            message="向量化失败",
            details=details,
            status_code=500
        )


# ============ 查询相关异常 (4xxx) ============

class QueryExecutionError(ASKPRDException):
    """查询执行失败"""

    def __init__(self, reason: str, details: Optional[Dict] = None):
        super().__init__(
            error_code="4001",
            message=f"查询执行失败: {reason}",
            details=details,
            status_code=500
        )


class BedrockAPIError(ASKPRDException):
    """Bedrock API调用失败"""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            error_code="4010",
            message="Bedrock API调用失败",
            details=details,
            status_code=503
        )


# ============ 系统异常 (9xxx) ============

class DatabaseError(ASKPRDException):
    """数据库错误"""

    def __init__(self, reason: str):
        super().__init__(
            error_code="9001",
            message=f"数据库错误: {reason}",
            details={"reason": reason},
            status_code=500
        )


class ConfigurationError(ASKPRDException):
    """配置错误"""

    def __init__(self, reason: str):
        super().__init__(
            error_code="9010",
            message=f"配置错误: {reason}",
            details={"reason": reason},
            status_code=500
        )
