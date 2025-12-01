# 快速开始指南

本指南将帮助你快速启动ASK-PRD后端服务。

## 前置要求

- Python 3.12+
- AWS账号（需配置Bedrock、S3、OpenSearch访问权限）
- 8GB+ RAM
- 10GB+ 磁盘空间

## 5分钟快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件（如果在开发服务器上已有权限，可跳过AWS密钥配置）
vim .env
```

最小配置：
```bash
# AWS配置
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key      # 可选（如已配置IAM角色）
AWS_SECRET_ACCESS_KEY=your-secret-key  # 可选（如已配置IAM角色）

# S3
S3_BUCKET=your-bucket-name
S3_PREFIX=aks-prd/

# OpenSearch
OPENSEARCH_ENDPOINT=your-opensearch-endpoint

# Bedrock
BEDROCK_REGION=us-west-2
GENERATION_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# 应用
DEBUG=true
LOG_LEVEL=INFO
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

输出示例：
```
✅ 数据库初始化成功！
数据库表:
  - knowledge_bases  (知识库)
  - documents        (文档)
  - chunks           (文本/图片块)
  - sync_tasks       (同步任务)
  - query_history    (查询历史)
```

### 4. 启动服务

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用简化命令：
```bash
python -m app.main
```

### 5. 验证安装

打开浏览器访问：

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

或使用curl测试：
```bash
# 健康检查
curl http://localhost:8000/health

# API根路径
curl http://localhost:8000/api/v1/
```

## 测试API

### 创建知识库

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的第一个知识库",
    "description": "测试知识库",
    "s3_bucket": "your-bucket",
    "s3_prefix": "test-kb/"
  }'
```

### 列出知识库

```bash
curl http://localhost:8000/api/v1/knowledge-bases
```

### 上传文档

```bash
curl -X POST "http://localhost:8000/api/v1/documents?kb_id=kb-xxx" \
  -F "file=@/path/to/document.pdf"
```

### 列出文档

```bash
curl "http://localhost:8000/api/v1/documents?kb_id=kb-xxx"
```

## 常见问题

### Q: ModuleNotFoundError: No module named 'xxx'

**解决**: 确保已安装所有依赖
```bash
pip install -r requirements.txt
```

### Q: OpenSearch连接失败

**原因**: OpenSearch endpoint未配置或无法访问

**解决**:
1. 检查`.env`中的`OPENSEARCH_ENDPOINT`配置
2. 确保OpenSearch集群正在运行
3. 检查网络连接和安全组配置
4. 验证IAM权限

### Q: S3上传失败

**原因**: S3权限不足或bucket不存在

**解决**:
1. 检查`.env`中的`S3_BUCKET`配置
2. 确保bucket存在且有写权限
3. 检查IAM角色/用户权限

### Q: Bedrock API错误

**原因**: 模型ID错误或区域不支持

**解决**:
1. 确认`BEDROCK_REGION`设置为`us-west-2`
2. 验证模型ID: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
3. 确保Bedrock服务已启用
4. 检查IAM权限（需要bedrock:InvokeModel权限）

### Q: 数据库locked错误

**原因**: SQLite并发访问限制

**解决**: 数据库已配置WAL模式，通常不会出现此问题。如果仍然出现：
```bash
# 删除旧数据库重新初始化
rm data/ask-prd.db*
python scripts/init_db.py
```

### Q: 如何查看详细日志

开发模式下日志会输出到控制台：
```bash
# 设置日志级别为DEBUG
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload
```

## 下一步

现在你已经成功启动了ASK-PRD后端服务！接下来可以：

1. **探索API**: 访问 http://localhost:8000/docs 查看完整的API文档
2. **阅读开发文档**: 查看 [DEVELOPMENT.md](./DEVELOPMENT.md) 了解详细的开发进度
3. **查看变更日志**: 查看 [CHANGELOG.md](./CHANGELOG.md) 了解最新功能
4. **开始开发**:
   - 实现PDF转换服务
   - 添加文本分块和向量化
   - 实现同步任务系统
   - 开发Agent功能

## 获取帮助

- **项目文档**: 查看 `docs/` 目录下的设计文档
- **代码示例**: 查看 `tests/` 目录下的测试用例
- **GitHub Issues**: 提交问题或功能请求

## 开发模式

### 热重载

使用`--reload`参数自动重载代码：
```bash
uvicorn app.main:app --reload
```

### 代码格式化

```bash
# 格式化代码
black app/ tests/ scripts/

# 排序导入
isort app/ tests/ scripts/

# 类型检查
mypy app/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=app tests/
```

## 生产部署

生产环境部署建议：

1. **使用Gunicorn + Uvicorn Workers**:
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

2. **设置环境变量**:
```bash
DEBUG=false
LOG_LEVEL=INFO
```

3. **使用更强大的数据库**: 考虑迁移到PostgreSQL或MySQL

4. **添加反向代理**: 使用Nginx或ALB

5. **配置HTTPS**: 使用SSL/TLS证书

详细部署文档请参考 [DEPLOYMENT.md](./DEPLOYMENT.md)（待创建）。
