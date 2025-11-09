#!/usr/bin/env python3
"""
Two-Stage系统快速测试脚本
用于验证核心模块是否正常工作
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_document_processor():
    """测试DocumentProcessor"""
    print("Testing DocumentProcessor...")
    from app.services.document_processor import DocumentProcessor
    from app.services.document_loader import DocumentContent

    processor = DocumentProcessor()

    # 模拟文档内容
    test_content = DocumentContent(
        doc_id="test-doc-12345678",
        doc_name="test.md",
        markdown_path="/tmp/test.md",
        markdown_text="""# 标题1

这是第一段内容。

这是第二段内容。

## 标题2

这是第三段内容。

![](img_001.png)

这是图片后的内容。
""",
        image_paths=[]
    )

    processed = processor.process(test_content)

    print(f"✓ 处理完成:")
    print(f"  - 短ID: {processed.doc_short_id}")
    print(f"  - Content块数: {len(processed.content)}")
    print(f"  - 引用数: {len(processed.references_map)}")
    print(f"  - 引用标记: {list(processed.references_map.keys())[:5]}")

    return True


def test_reference_extractor():
    """测试ReferenceExtractor"""
    print("\nTesting ReferenceExtractor...")
    from app.services.reference_extractor import ReferenceExtractor, Stage1Result

    extractor = ReferenceExtractor()

    # 模拟答案文本
    answer_text = """
根据[DOC-abc12345-PARA-1]的描述，JOIN是一款社交App。
如[DOC-abc12345-IMAGE-1]所示，产品架构包含多个模块。
参考[DOC-def67890-PARA-3]，登录功能在v2版本进行了优化。
"""

    # 模拟Stage1结果
    stage1_results = [
        Stage1Result(
            doc_id="abc12345-1234-1234-1234-123456789012",
            doc_name="产品需求v1.md",
            doc_short_id="abc12345",
            response_text="...",
            references_map={
                "DOC-abc12345-PARA-1": "JOIN是一款专为年轻人设计的社交App",
                "DOC-abc12345-IMAGE-1": "img_001.png"
            }
        ),
        Stage1Result(
            doc_id="def67890-1234-1234-1234-123456789012",
            doc_name="产品需求v2.md",
            doc_short_id="def67890",
            response_text="...",
            references_map={
                "DOC-def67890-PARA-3": "登录功能增加了微信登录支持"
            }
        )
    ]

    references = extractor.extract_references(answer_text, stage1_results)

    print(f"✓ 提取完成:")
    print(f"  - 引用数量: {len(references)}")
    for ref in references:
        print(f"  - {ref.ref_id}: type={ref.chunk_type}, doc={ref.doc_name}")

    return True


def test_group_chunks():
    """测试_group_chunks_by_document修复"""
    print("\nTesting _group_chunks_by_document...")
    from app.services.query_service import QueryService

    # 模拟OpenSearch返回格式
    test_chunks = [
        {
            'id': 'chunk-001',
            'score': 0.95,
            'source': {
                'chunk_id': 'chunk-001',
                'document_id': 'doc-abc',
                'kb_id': 'kb-123',
                'content': 'test content 1'
            }
        },
        {
            'id': 'chunk-002',
            'score': 0.92,
            'source': {
                'chunk_id': 'chunk-002',
                'document_id': 'doc-abc',
                'kb_id': 'kb-123',
                'content': 'test content 2'
            }
        },
        {
            'id': 'chunk-003',
            'score': 0.88,
            'source': {
                'chunk_id': 'chunk-003',
                'document_id': 'doc-def',
                'kb_id': 'kb-123',
                'content': 'test content 3'
            }
        }
    ]

    result = QueryService._group_chunks_by_document(test_chunks)

    print(f"✓ 分组完成:")
    print(f"  - 文档数: {len(result)}")
    for doc_id, data in result.items():
        print(f"  - {doc_id}: {len(data['chunks'])} chunks")

    assert 'doc-abc' in result
    assert 'doc-def' in result
    assert len(result['doc-abc']['chunks']) == 2
    assert len(result['doc-def']['chunks']) == 1

    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Two-Stage System Unit Tests")
    print("=" * 60)

    tests = [
        test_document_processor,
        test_reference_extractor,
        test_group_chunks
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_func.__name__} PASSED")
            else:
                failed += 1
                print(f"✗ {test_func.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
