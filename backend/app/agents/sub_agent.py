"""
Sub-Agent实现
负责深度阅读单个文档并回答问题
"""
from typing import Dict, List
from pydantic import BaseModel
from strands import Agent
from strands.models import BedrockModel

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.tools.document_tools import (
    create_document_reader_tool,
    create_image_reader_tool,
    create_search_context_tool
)

logger = get_logger(__name__)


class SubAgentAnswer(BaseModel):
    """Sub-Agent的回答结构"""
    document_id: str
    document_name: str
    has_relevant_info: bool  # 是否包含相关信息
    answer: str  # 从该文档提取的答案
    confidence: float  # 置信度 0-1
    cited_chunks: List[str]  # 引用的chunk IDs


def create_sub_agent(
    document_id: str,
    document_name: str,
    markdown_content: str,
    images: List[Dict],
    relevant_context: str = ""
) -> Agent:
    """
    创建Sub-Agent实例

    Args:
        document_id: 文档ID
        document_name: 文档名称
        markdown_content: Markdown内容
        images: 图片信息列表
        relevant_context: 相关上下文（可选）

    Returns:
        Strands Agent实例
    """
    logger.info(
        "creating_sub_agent",
        document_id=document_id,
        document_name=document_name
    )

    # 创建Bedrock模型
    model = BedrockModel(
        model_id=settings.generation_model_id,
        region_name=settings.bedrock_region,
        temperature=0.3,
        max_tokens=2000
    )

    # 创建文档阅读工具
    read_doc_tool = create_document_reader_tool(markdown_content, images)
    read_images_tool = create_image_reader_tool(images)

    tools = [read_doc_tool, read_images_tool]

    # 如果有上下文，添加上下文工具
    if relevant_context:
        context_tool = create_search_context_tool(relevant_context)
        tools.append(context_tool)

    # 构建系统提示词
    system_prompt = f"""你是一个专业的文档分析助手，负责深度阅读文档并回答问题。

当前文档: {document_name}
文档ID: {document_id}

你的任务:
1. 使用提供的工具读取文档内容和图片信息
2. 仔细分析用户的问题
3. 从文档中提取相关信息回答问题
4. 如果文档中没有相关信息，明确说明
5. 引用具体的文本或图片内容支撑你的回答

注意事项:
- 只基于文档内容回答，不要编造信息
- 如果涉及图片，请详细描述图片内容
- 保持客观和准确
- 使用中文回答
"""

    # 创建Agent
    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        name=f"SubAgent-{document_id[:8]}"
    )

    return agent


async def invoke_sub_agent(
    agent: Agent,
    query: str,
    document_id: str,
    document_name: str
) -> Dict:
    """
    调用Sub-Agent

    Args:
        agent: Sub-Agent实例
        query: 用户问题
        document_id: 文档ID
        document_name: 文档名称

    Returns:
        Sub-Agent的回答
    """
    logger.info(
        "invoking_sub_agent",
        document_id=document_id,
        query=query[:50]
    )

    try:
        # 使用structured_output获取结构化回答
        # 注意：这里简化处理，实际可以定义更复杂的输出结构
        result = await agent.invoke_async(query)

        # 提取回答
        answer_text = ""
        if hasattr(result, 'output'):
            if isinstance(result.output, str):
                answer_text = result.output
            elif isinstance(result.output, dict):
                answer_text = result.output.get('text', '')
        else:
            answer_text = str(result)

        # 获取metrics
        token_usage = {}
        if hasattr(result, 'metrics') and result.metrics:
            usage = result.metrics.accumulated_usage
            token_usage = {
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0)
            }

        logger.info(
            "sub_agent_completed",
            document_id=document_id,
            answer_length=len(answer_text),
            tokens=token_usage.get("total_tokens", 0)
        )

        return {
            "document_id": document_id,
            "document_name": document_name,
            "answer": answer_text,
            "has_relevant_info": len(answer_text) > 50,  # 简单判断
            "confidence": 0.8,  # 简化处理，实际可以更复杂
            "token_usage": token_usage
        }

    except Exception as e:
        logger.error(
            "sub_agent_failed",
            document_id=document_id,
            error=str(e),
            exc_info=True
        )

        return {
            "document_id": document_id,
            "document_name": document_name,
            "answer": f"处理文档时出错: {str(e)}",
            "has_relevant_info": False,
            "confidence": 0.0,
            "token_usage": {}
        }
