#!/usr/bin/env python3
"""
测试单个文档的同步处理
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.workers.sync_worker import SyncWorker
from app.models.database import Document

async def test_sync():
    """测试同步单个文档"""
    db = SessionLocal()

    try:
        # 获取文档
        doc_id = "doc-4dc3d2e5-badd-4314-bffa-d01a8cf4ae14"
        doc = db.query(Document).filter(Document.id == doc_id).first()

        if not doc:
            print(f"❌ 文档不存在: {doc_id}")
            return

        print(f"✅ 找到文档: {doc.filename}")
        print(f"   状态: {doc.status}")
        print(f"   PDF路径: {doc.local_pdf_path}")
        print(f"   PDF存在: {Path(doc.local_pdf_path).exists() if doc.local_pdf_path else False}")

        # 处理文档
        print(f"\n📝 开始处理文档...")
        success = await SyncWorker._process_single_document(db, doc)

        if success:
            print(f"✅ 文档处理成功")
            # 刷新文档状态
            db.refresh(doc)
            print(f"   新状态: {doc.status}")
            print(f"   Markdown: {doc.local_markdown_path}")
            print(f"   Text Markdown: {doc.local_text_markdown_path}")
        else:
            print(f"❌ 文档处理失败")
            db.refresh(doc)
            print(f"   状态: {doc.status}")
            print(f"   错误: {doc.error_message}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sync())
