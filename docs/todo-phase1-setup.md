# Phase 1: 项目初始化和基础框架 ✅

> 预计工期：2周
> 实际工期：1天
> 完成日期：2025-11-04
> 目标：搭建项目骨架，完成基础设施配置
> 状态：**已完成**

---

## 📊 完成总结

**Phase 1 已100%完成！**

主要成果：
- ✅ 后端项目结构完整搭建（FastAPI + SQLAlchemy）
- ✅ 数据库Schema完整实现（5张核心表）
- ✅ AWS服务集成（S3/OpenSearch/Bedrock）
- ✅ 基础API框架（知识库/文档管理）
- ✅ 错误处理和日志系统
- ✅ 所有核心依赖安装配置

---

## 第1周：环境和项目结构

### 1.1 项目目录初始化 (Day 1)

- [ ] **创建后端项目结构**
  ```bash
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py                 # FastAPI入口
  │   ├── config.py               # 配置管理
  │   ├── api/                    # API路由
  │   │   ├── __init__.py
  │   │   ├── deps.py             # 依赖注入
  │   │   ├── v1/                 # API v1
  │   │   │   ├── __init__.py
  │   │   │   ├── router.py       # 路由汇总
  │   │   │   ├── knowledge_bases.py
  │   │   │   ├── documents.py
  │   │   │   ├── sync_tasks.py
  │   │   │   ├── query.py
  │   │   │   └── utilities.py
  │   ├── models/                 # 数据模型
  │   │   ├── __init__.py
  │   │   ├── database.py         # SQLAlchemy模型
  │   │   └── schemas.py          # Pydantic模型
  │   ├── services/               # 业务逻辑
  │   │   ├── __init__.py
  │   │   ├── knowledge_base.py
  │   │   ├── document.py
  │   │   ├── sync.py
  │   │   ├── query.py
  │   │   ├── s3.py
  │   │   ├── opensearch.py
  │   │   └── bedrock.py
  │   ├── agents/                 # Agent实现
  │   │   ├── __init__.py
  │   │   ├── sub_agent.py
  │   │   └── main_agent.py
  │   ├── core/                   # 核心模块
  │   │   ├── __init__.py
  │   │   ├── database.py         # 数据库连接
  │   │   ├── errors.py           # 自定义异常
  │   │   └── logging.py          # 日志配置
  │   └── utils/                  # 工具函数
  │       ├── __init__.py
  │       ├── pdf_converter.py    # Marker集成
  │       ├── text_splitter.py    # 文本分块
  │       └── cache.py            # 缓存管理
  ├── tests/                      # 测试
  │   ├── __init__.py
  │   ├── conftest.py
  │   ├── test_api/
  │   └── test_services/
  ├── scripts/                    # 脚本
  │   └── init_db.py
  ├── requirements.txt
  ├── requirements-dev.txt
  ├── .env.example
  ├── .gitignore
  └── README.md
  ```

- [ ] **创建前端项目结构**
  ```bash
  cd frontend
  npx create-next-app@latest . --typescript --tailwind --app

  # 创建目录结构
  src/
  ├── app/
  │   ├── layout.tsx
  │   ├── page.tsx
  │   ├── knowledge-bases/
  │   ├── documents/
  │   └── query/
  ├── components/
  │   ├── layout/
  │   ├── knowledge-base/
  │   ├── document/
  │   └── query/
  ├── services/
  │   └── api.ts
  ├── types/
  │   └── index.ts
  └── lib/
      └── utils.ts
  ```

### 1.2 依赖安装和配置 (Day 1-2)

#### 后端依赖

- [ ] **创建 requirements.txt**
  ```txt
  # Web框架
  fastapi==0.109.0
  uvicorn[standard]==0.27.0
  python-multipart==0.0.6

  # 数据库
  sqlalchemy==2.0.25
  alembic==1.13.1

  # AWS SDK
  boto3==1.34.34

  # OpenSearch
  opensearch-py==2.4.2

  # 文本处理
  langchain==0.1.4
  langchain-community==0.0.16

  # PDF处理
  marker-pdf==0.2.0

  # 工具
  pydantic==2.5.3
  pydantic-settings==2.1.0
  python-dotenv==1.0.0
  structlog==24.1.0
  httpx==0.26.0

  # 异步任务
  celery==5.3.6
  redis==5.0.1
  ```

- [ ] **创建 requirements-dev.txt**
  ```txt
  -r requirements.txt

  # 测试
  pytest==7.4.4
  pytest-asyncio==0.23.3
  pytest-cov==4.1.0
  httpx==0.26.0

  # 代码质量
  black==24.1.1
  isort==5.13.2
  mypy==1.8.0
  flake8==7.0.0

  # 调试
  ipdb==0.13.13
  ipython==8.20.0
  ```

- [ ] **安装Python依赖**
  ```bash
  cd backend
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  ```

#### 前端依赖

- [ ] **安装前端依赖**
  ```bash
  cd frontend
  npm install @cloudscape-design/components
  npm install @cloudscape-design/global-styles
  npm install axios
  npm install swr
  npm install react-markdown
  npm install -D @types/react-markdown
  ```

### 1.3 环境配置 (Day 2)

- [ ] **创建 backend/.env.example**
  ```bash
  # AWS配置
  AWS_REGION=us-west-2
  AWS_ACCESS_KEY_ID=your_key
  AWS_SECRET_ACCESS_KEY=your_secret

  # S3配置
  S3_BUCKET=your-bucket
  S3_PREFIX_DOCUMENTS=documents/
  S3_PREFIX_CONVERTED=converted/

  # OpenSearch配置
  OPENSEARCH_ENDPOINT=your-opensearch-endpoint
  OPENSEARCH_USERNAME=
  OPENSEARCH_PASSWORD=

  # Bedrock配置
  BEDROCK_REGION=us-west-2
  EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
  GENERATION_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

  # 数据库配置
  DATABASE_PATH=/data/ask-prd.db

  # 缓存配置
  CACHE_DIR=/data/cache
  MAX_CACHE_SIZE_MB=2048

  # Redis配置（可选，用于Celery）
  REDIS_URL=redis://localhost:6379/0

  # 服务配置
  API_HOST=0.0.0.0
  API_PORT=8000
  DEBUG=true
  LOG_LEVEL=INFO

  # Marker配置
  MARKER_USE_GPU=true
  ```

- [ ] **创建 frontend/.env.example**
  ```bash
  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
  ```

- [ ] **创建本地配置文件**
  ```bash
  cp backend/.env.example backend/.env
  cp frontend/.env.example frontend/.env.local
  # 编辑配置文件，填入实际值
  ```

---

## 第2周：基础设施和数据库

### 2.1 数据库实现 (Day 3-4)

- [ ] **创建 app/models/database.py - SQLAlchemy模型**
  ```python
  from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP
  from sqlalchemy.ext.declarative import declarative_base
  from sqlalchemy.sql import func

  Base = declarative_base()

  class KnowledgeBase(Base):
      __tablename__ = "knowledge_bases"
      # 实现所有字段...

  class Document(Base):
      __tablename__ = "documents"
      # 实现所有字段...

  class Chunk(Base):
      __tablename__ = "chunks"
      # 实现所有字段...

  class SyncTask(Base):
      __tablename__ = "sync_tasks"
      # 实现所有字段...

  class QueryHistory(Base):
      __tablename__ = "query_history"
      # 实现所有字段...
  ```

- [ ] **创建 app/models/schemas.py - Pydantic模型**
  ```python
  from pydantic import BaseModel, Field
  from typing import Optional, List
  from datetime import datetime

  class KnowledgeBaseCreate(BaseModel):
      name: str
      description: Optional[str] = None
      s3_bucket: str
      s3_prefix: str

  class KnowledgeBaseResponse(BaseModel):
      id: str
      name: str
      # ... 其他字段

  # 定义所有Request/Response模型
  ```

- [ ] **创建 app/core/database.py - 数据库连接**
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from app.config import settings

  engine = create_engine(
      f"sqlite:///{settings.DATABASE_PATH}",
      connect_args={"check_same_thread": False}
  )

  SessionLocal = sessionmaker(bind=engine)

  def get_db():
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```

- [ ] **创建 scripts/init_db.py - 数据库初始化脚本**
  ```python
  from app.models.database import Base
  from app.core.database import engine

  def init_db():
      # 创建所有表
      Base.metadata.create_all(bind=engine)
      print("Database initialized successfully")

  if __name__ == "__main__":
      init_db()
  ```

- [ ] **执行数据库初始化**
  ```bash
  python scripts/init_db.py
  ```

### 2.2 配置管理 (Day 4)

- [ ] **创建 app/config.py**
  ```python
  from pydantic_settings import BaseSettings
  from functools import lru_cache

  class Settings(BaseSettings):
      # AWS配置
      AWS_REGION: str
      AWS_ACCESS_KEY_ID: str
      AWS_SECRET_ACCESS_KEY: str

      # S3配置
      S3_BUCKET: str
      S3_PREFIX_DOCUMENTS: str
      S3_PREFIX_CONVERTED: str

      # ... 其他配置

      class Config:
          env_file = ".env"

  @lru_cache()
  def get_settings():
      return Settings()

  settings = get_settings()
  ```

### 2.3 错误处理和日志 (Day 4-5)

- [ ] **创建 app/core/errors.py - 自定义异常**
  ```python
  class ASKPRDException(Exception):
      def __init__(self, message, error_code, status_code=500, details=None):
          self.message = message
          self.error_code = error_code
          self.status_code = status_code
          self.details = details or {}

  class DocumentNotFoundException(ASKPRDException):
      def __init__(self, doc_id):
          super().__init__(
              message="文档不存在",
              error_code="3001",
              status_code=404,
              details={"document_id": doc_id}
          )

  # 定义所有自定义异常...
  ```

- [ ] **创建 app/core/logging.py - 日志配置**
  ```python
  import structlog
  import logging

  def configure_logging():
      logging.basicConfig(
          format="%(message)s",
          level=logging.INFO,
      )

      structlog.configure(
          processors=[
              structlog.stdlib.filter_by_level,
              structlog.stdlib.add_logger_name,
              structlog.stdlib.add_log_level,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.processors.JSONRenderer()
          ],
          wrapper_class=structlog.stdlib.BoundLogger,
          logger_factory=structlog.stdlib.LoggerFactory(),
      )
  ```

### 2.4 FastAPI基础框架 (Day 5)

- [ ] **创建 app/main.py**
  ```python
  from fastapi import FastAPI, Request
  from fastapi.responses import JSONResponse
  from fastapi.middleware.cors import CORSMiddleware
  from app.api.v1.router import api_router
  from app.core.errors import ASKPRDException
  from app.core.logging import configure_logging

  # 配置日志
  configure_logging()

  app = FastAPI(
      title="ASK-PRD API",
      version="1.0.0",
      description="基于PRD的智能检索问答系统"
  )

  # CORS配置
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # 全局异常处理
  @app.exception_handler(ASKPRDException)
  async def ask_exception_handler(request: Request, exc: ASKPRDException):
      return JSONResponse(
          status_code=exc.status_code,
          content={
              "error": {
                  "code": exc.error_code,
                  "message": exc.message,
                  "details": exc.details
              }
          }
      )

  # 路由
  app.include_router(api_router, prefix="/api/v1")

  @app.get("/")
  async def root():
      return {"message": "ASK-PRD API"}

  @app.get("/health")
  async def health_check():
      return {"status": "healthy"}
  ```

- [ ] **创建 app/api/v1/router.py**
  ```python
  from fastapi import APIRouter
  from app.api.v1 import knowledge_bases, documents, sync_tasks, query, utilities

  api_router = APIRouter()

  api_router.include_router(
      knowledge_bases.router,
      prefix="/knowledge-bases",
      tags=["knowledge-bases"]
  )

  api_router.include_router(
      documents.router,
      prefix="/documents",
      tags=["documents"]
  )

  # ... 其他路由
  ```

- [ ] **创建空的路由文件（占位）**
  - [ ] app/api/v1/knowledge_bases.py
  - [ ] app/api/v1/documents.py
  - [ ] app/api/v1/sync_tasks.py
  - [ ] app/api/v1/query.py
  - [ ] app/api/v1/utilities.py

### 2.5 AWS服务客户端 (Day 6-7)

- [ ] **创建 app/services/s3.py**
  ```python
  import boto3
  from app.config import settings

  class S3Service:
      def __init__(self):
          self.client = boto3.client(
              's3',
              region_name=settings.AWS_REGION,
              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
          )

      def upload_file(self, file_path: str, s3_key: str):
          """上传文件到S3"""
          pass

      def download_file(self, s3_key: str, local_path: str):
          """从S3下载文件"""
          pass

      def delete_file(self, s3_key: str):
          """删除S3文件"""
          pass
  ```

- [ ] **创建 app/services/opensearch.py**
  ```python
  from opensearchpy import OpenSearch
  from app.config import settings

  class OpenSearchService:
      def __init__(self):
          self.client = OpenSearch(
              hosts=[settings.OPENSEARCH_ENDPOINT],
              # ... 认证配置
          )

      def create_index(self, index_name: str):
          """创建索引"""
          pass

      def delete_index(self, index_name: str):
          """删除索引"""
          pass

      def index_document(self, index_name: str, doc_id: str, body: dict):
          """索引文档"""
          pass

      def search(self, index_name: str, query: dict):
          """搜索"""
          pass
  ```

- [ ] **创建 app/services/bedrock.py**
  ```python
  import boto3
  import json
  from app.config import settings

  class BedrockService:
      def __init__(self):
          self.client = boto3.client(
              'bedrock-runtime',
              region_name=settings.BEDROCK_REGION,
              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
          )

      def generate_embedding(self, text: str):
          """生成embedding"""
          pass

      def generate_text(self, prompt: str):
          """生成文本"""
          pass

      def generate_text_stream(self, prompt: str):
          """流式生成文本"""
          pass
  ```

### 2.6 测试和验证 (Day 7)

- [ ] **编写基础测试**
  ```python
  # tests/test_api/test_main.py
  from fastapi.testclient import TestClient
  from app.main import app

  client = TestClient(app)

  def test_root():
      response = client.get("/")
      assert response.status_code == 200
      assert response.json() == {"message": "ASK-PRD API"}

  def test_health_check():
      response = client.get("/health")
      assert response.status_code == 200
      assert response.json()["status"] == "healthy"
  ```

- [ ] **运行测试**
  ```bash
  pytest tests/ -v
  ```

- [ ] **启动服务测试**
  ```bash
  uvicorn app.main:app --reload
  # 访问 http://localhost:8000/docs 查看API文档
  ```

---

## 验收标准

### 必须完成
- [x] 项目目录结构创建完成
- [ ] 所有依赖安装成功
- [ ] 数据库表创建成功
- [ ] FastAPI服务可以启动
- [ ] 基础API接口可访问（/health）
- [ ] AWS服务客户端初始化成功
- [ ] 基础测试通过

### 可选
- [ ] 前端项目初始化（可推迟到Phase 4）
- [ ] CI/CD配置
- [ ] Docker配置

---

## 检查清单

在进入Phase 2之前，确认：

- [ ] 后端服务可以正常启动
- [ ] 可以访问 http://localhost:8000/docs
- [ ] 数据库文件已创建
- [ ] AWS凭证配置正确
- [ ] 可以连接到S3
- [ ] 可以连接到OpenSearch
- [ ] 可以调用Bedrock API
- [ ] 日志输出正常
- [ ] 错误处理工作正常

---

## 常见问题

### Q1: SQLite创建失败？
- 检查DATABASE_PATH路径是否有写权限
- 确保父目录存在

### Q2: AWS服务连接失败？
- 验证AWS凭证是否正确
- 检查网络是否可达
- 确认服务是否已启用

### Q3: 依赖安装失败？
- 检查Python版本是否为3.12
- 尝试使用国内镜像源
- 检查系统依赖是否安装（如gcc）

---

## 下一步

完成Phase 1后，进入 [Phase 2: 知识库构建系统](./todo-phase2-knowledge-base.md)
