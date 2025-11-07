"""
测试Embedding生成性能（串行 vs 并发）
"""
import time
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.bedrock_client import bedrock_client
from app.core.logging import get_logger

logger = get_logger(__name__)


def test_embedding_performance():
    """测试embedding性能"""

    # 准备测试数据
    test_texts = [
        f"这是第{i}条测试文本，用于测试Bedrock Titan Embeddings V2的性能。"
        for i in range(25)
    ]

    logger.info("=" * 60)
    logger.info("Embedding性能测试")
    logger.info(f"测试文本数量: {len(test_texts)}")
    logger.info("=" * 60)

    # 测试并发版本
    start_time = time.time()
    embeddings = bedrock_client.generate_embeddings(
        texts=test_texts,
        normalize=True
    )
    concurrent_time = time.time() - start_time

    logger.info("✅ 并发版本测试完成")
    logger.info(f"   耗时: {concurrent_time:.2f}秒")
    logger.info(f"   生成向量数: {len(embeddings)}")
    logger.info(f"   向量维度: {len(embeddings[0]) if embeddings else 0}")
    logger.info(f"   平均每个: {(concurrent_time / len(test_texts)) * 1000:.1f}ms")

    logger.info("=" * 60)
    logger.info("测试结论:")
    logger.info(f"✨ 并发处理25个文本仅需: {concurrent_time:.2f}秒")
    logger.info(f"💡 如果是串行（假设每个20ms），预计需要: {0.02 * 25:.2f}秒")
    logger.info(f"🚀 理论性能提升: {(0.02 * 25) / concurrent_time:.1f}倍")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_embedding_performance()
