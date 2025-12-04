"""
应用配置模块
使用pydantic-settings管理配置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # AWS配置
    aws_region: str = "us-west-2"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # S3配置
    s3_bucket: str

    # OpenSearch配置
    opensearch_endpoint: str

    # Bedrock配置
    bedrock_region: str = "us-west-2"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    generation_model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # Bedrock跨账号配置（可选）
    # 如果配置了这两个字段，Bedrock将使用专用凭证（跨账号访问）
    # 如果不配置，将使用aws_access_key_id/aws_secret_access_key或EC2 IAM Role
    bedrock_aws_access_key_id: Optional[str] = None
    bedrock_aws_secret_access_key: Optional[str] = None

    # 本地存储配置
    data_dir: str = "./data"

    # 数据库配置
    database_path: str = "./data/ask-prd.db"

    # 缓存配置
    cache_dir: str = "./data/cache"
    max_cache_size_mb: int = 2048

    # 服务配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    # 查询配置
    max_retrieval_docs: int = 20  # 检索的最大文档数
    stage1_concurrency: int = 5  # Stage 1文档处理的最大并发数

    # Marker配置
    marker_use_gpu: bool = True

    # JWT认证配置
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_days: int = 7

    @property
    def JWT_SECRET_KEY(self) -> str:
        """JWT密钥（大写属性，兼容security.py）"""
        return self.jwt_secret_key

    @property
    def JWT_ALGORITHM(self) -> str:
        """JWT算法（大写属性，兼容security.py）"""
        return self.jwt_algorithm

    @property
    def JWT_ACCESS_TOKEN_EXPIRE_DAYS(self) -> int:
        """JWT过期天数（大写属性，兼容security.py）"""
        return self.jwt_access_token_expire_days

    @property
    def database_url(self) -> str:
        """SQLite数据库连接URL"""
        return f"sqlite:///{self.database_path}"

    @property
    def pdf_dir(self) -> str:
        """PDF存储目录"""
        return os.path.join(self.data_dir, "documents", "pdfs")

    @property
    def markdown_dir(self) -> str:
        """Markdown存储目录"""
        return os.path.join(self.data_dir, "documents", "markdowns")

    @property
    def text_markdown_dir(self) -> str:
        """纯文本Markdown存储目录"""
        return os.path.join(self.data_dir, "documents", "text_markdowns")


# 全局配置实例
settings = Settings()
