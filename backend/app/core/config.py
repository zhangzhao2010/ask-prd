"""
应用配置模块
使用pydantic-settings管理配置
"""
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

    # 数据库配置
    database_path: str = "./data/aks-prd.db"

    # 缓存配置
    cache_dir: str = "./data/cache"
    max_cache_size_mb: int = 2048

    # 服务配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    # Marker配置
    marker_use_gpu: bool = True

    @property
    def database_url(self) -> str:
        """SQLite数据库连接URL"""
        return f"sqlite:///{self.database_path}"


# 全局配置实例
settings = Settings()
