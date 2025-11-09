"""
ReferenceExtractor模块
负责从答案中提取和格式化引用
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Reference:
    """引用对象数据类"""
    ref_id: str              # 例如: "DOC-abc12345-PARA-5"
    doc_id: str              # 完整document_id
    doc_name: str            # 文档名称
    chunk_type: str          # "text" 或 "image"
    content: Optional[str]   # 文本chunk的内容
    image_url: Optional[str] # 图片chunk的URL


@dataclass
class Stage1Result:
    """Stage 1的处理结果"""
    doc_id: str
    doc_name: str
    doc_short_id: str
    response_text: str               # 大模型返回的结构化文本
    references_map: dict             # {ref_id: 内容}


class ReferenceExtractor:
    """负责从答案中提取和格式化引用"""

    def extract_references(
        self,
        answer_text: str,
        stage1_results: List[Stage1Result]
    ) -> List[Reference]:
        """
        从答案中提取引用标记，并构建引用对象

        Args:
            answer_text: Stage 2生成的完整答案
            stage1_results: 所有Stage 1的结果

        Returns:
            引用对象列表
        """
        logger.info(
            "extracting_references",
            answer_length=len(answer_text),
            stage1_results_count=len(stage1_results)
        )

        # 1. 提取所有引用标记
        ref_ids = self._extract_ref_ids(answer_text)

        logger.info("found_reference_ids", count=len(ref_ids), ref_ids=ref_ids[:10])

        # 2. 构建引用对象
        references = []
        for ref_id in ref_ids:
            ref = self._build_reference(ref_id, stage1_results)
            if ref:
                references.append(ref)
            else:
                logger.warning("reference_not_found", ref_id=ref_id)

        logger.info("references_extracted", count=len(references))

        return references

    def _extract_ref_ids(self, text: str) -> List[str]:
        """
        从文本中提取所有引用标记

        Args:
            text: 文本内容

        Returns:
            去重后的引用标记列表
        """
        # 正则匹配 [DOC-xxxxxxxx-PARA-Y] 或 [DOC-xxxxxxxx-IMAGE-Z]
        # doc_short_id是8位十六进制字符
        pattern = r'\[(DOC-[a-f0-9]{8}-(PARA|IMAGE)-\d+)\]'
        matches = re.findall(pattern, text, re.IGNORECASE)

        # 提取第一个捕获组（ref_id）
        ref_ids = [match[0] for match in matches]

        # 去重并保持顺序
        seen = set()
        unique_refs = []
        for ref_id in ref_ids:
            if ref_id not in seen:
                seen.add(ref_id)
                unique_refs.append(ref_id)

        return unique_refs

    def _build_reference(
        self,
        ref_id: str,
        stage1_results: List[Stage1Result]
    ) -> Optional[Reference]:
        """
        根据ref_id构建引用对象

        Args:
            ref_id: 例如 "DOC-abc12345-PARA-5"
            stage1_results: 所有Stage 1的结果

        Returns:
            Reference对象，如果找不到则返回None
        """
        # 1. 解析ref_id，提取doc_short_id
        # ref_id格式: DOC-{short_id}-(PARA|IMAGE)-{number}
        # 例如：DOC-doc-3931-PARA-13 或 DOC-abc12345-IMAGE-2
        # 注意：doc_short_id可能包含连字符，所以使用正则表达式而不是简单split
        import re
        match = re.match(r'^DOC-(.+?)-(PARA|IMAGE)-(\d+)$', ref_id, re.IGNORECASE)

        if not match:
            logger.warning("invalid_ref_id_format", ref_id=ref_id)
            return None

        doc_short_id = match.group(1)  # 提取doc_short_id（可能包含连字符）
        chunk_type_raw = match.group(2)  # "PARA" 或 "IMAGE"
        chunk_type = "text" if chunk_type_raw.upper() == "PARA" else "image"

        # 2. 从stage1_results中查找对应的文档
        target_result = None
        for result in stage1_results:
            if result.doc_short_id.lower() == doc_short_id.lower():
                target_result = result
                break

        if not target_result:
            logger.warning(
                "doc_not_found_for_ref",
                ref_id=ref_id,
                doc_short_id=doc_short_id
            )
            return None

        # 3. 从references_map中查找内容
        if ref_id not in target_result.references_map:
            logger.warning(
                "ref_id_not_in_map",
                ref_id=ref_id,
                doc_id=target_result.doc_id
            )
            return None

        content_or_path = target_result.references_map[ref_id]

        # 4. 构建引用对象
        if chunk_type == "text":
            return Reference(
                ref_id=ref_id,
                doc_id=target_result.doc_id,
                doc_name=target_result.doc_name,
                chunk_type="text",
                content=content_or_path,
                image_url=None
            )
        else:
            # 图片类型，content_or_path是图片文件名
            image_url = f"/api/v1/documents/{target_result.doc_id}/images/{content_or_path}"
            return Reference(
                ref_id=ref_id,
                doc_id=target_result.doc_id,
                doc_name=target_result.doc_name,
                chunk_type="image",
                content=None,
                image_url=image_url
            )
