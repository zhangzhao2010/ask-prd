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

    # OpenSearch配置
    opensearch_endpoint: str

    # Bedrock配置
    bedrock_region: str = "us-west-2"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    generation_model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

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

    # Marker配置
    marker_use_gpu: bool = True

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
