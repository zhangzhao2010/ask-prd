"""
Main-Agent实现
负责综合多个Sub-Agent的结果生成最终答案
"""
from typing import List, Dict, AsyncGenerator
from strands import Agent
from strands.models import BedrockModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_main_agent() -> Agent:
    """
    创建Main-Agent实例

    Returns:
        Strands Agent实例
    """
    logger.info("creating_main_agent")

    # 创建Bedrock模型（启用流式输出）
    model = BedrockModel(
        model_id=settings.generation_model_id,
        region_name=settings.bedrock_region,
        temperature=0.5,
        max_tokens=4096,
        streaming=True
    )

    # 系统提示词
    system_prompt = """你是一个专业的知识综合助手，负责整合多个文档的分析结果，生成完整准确的答案。

你的任务:
1. 接收多个文档的分析结果
2. 识别不同文档之间的共同点和差异
3. 综合信息生成全面的答案
4. 清晰地标注信息来源
5. 如果信息有冲突，指出并分析原因

回答格式要求:
- 使用结构化的Markdown格式
- 明确标注引用来源（文档名称）
- 如果涉及演进历史，按时间顺序组织
- 如果涉及流程，使用清晰的步骤说明
- 保持客观和准确

使用中文回答。
"""

    # 创建Agent（无需工具，直接基于输入的文档结果）
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        name="MainAgent"
    )

    return agent


async def invoke_main_agent_stream(
    agent: Agent,
    query: str,
    sub_agent_results: List[Dict]
) -> AsyncGenerator[Dict, None]:
    """
    流式调用Main-Agent

    Args:
        agent: Main-Agent实例
        query: 用户问题
        sub_agent_results: Sub-Agent的结果列表

    Yields:
        流式事件
    """
    logger.info(
        "invoking_main_agent_stream",
        query=query[:50],
        num_documents=len(sub_agent_results)
    )

    # 构建提示词
    prompt = f"""用户问题: {query}

我已经分析了 {len(sub_agent_results)} 个相关文档，以下是每个文档的分析结果：

"""

    # 添加每个文档的结果
    for idx, result in enumerate(sub_agent_results, 1):
        doc_name = result.get("document_name", "未知文档")
        answer = result.get("answer", "无内容")
        has_info = result.get("has_relevant_info", False)

        if has_info:
            prompt += f"""
## 文档 {idx}: {doc_name}

{answer}

---

"""

    prompt += """
请基于以上文档的分析结果，综合回答用户的问题。

要求:
1. 整合所有相关信息
2. 清晰标注信息来源
3. 如果有演进历史，按时间顺序说明
4. 如果有矛盾，指出并分析
5. 使用Markdown格式，结构清晰
"""

    try:
        # 流式调用
        total_tokens = 0
        answer_text = ""

        async for event in agent.stream_async(prompt):
            # 文本增量事件
            if text_delta := event.get("text_delta"):
                answer_text += text_delta
                yield {
                    "type": "text_delta",
                    "content": text_delta
                }

            # 完成事件
            elif event.get("stop_reason"):
                # 获取token统计
                if metrics := event.get("metrics"):
                    usage = metrics.get("usage", {})
                    total_tokens = usage.get("totalTokens", 0)

                logger.info(
                    "main_agent_completed",
                    answer_length=len(answer_text),
                    total_tokens=total_tokens
                )

                yield {
                    "type": "complete",
                    "total_tokens": total_tokens
                }

    except Exception as e:
        logger.error(
            "main_agent_failed",
            error=str(e),
            exc_info=True
        )

        yield {
            "type": "error",
            "message": f"生成答案时出错: {str(e)}"
        }


async def invoke_main_agent(
    agent: Agent,
    query: str,
    sub_agent_results: List[Dict]
) -> Dict:
    """
    非流式调用Main-Agent

    Args:
        agent: Main-Agent实例
        query: 用户问题
        sub_agent_results: Sub-Agent的结果列表

    Returns:
        Main-Agent的回答
    """
    logger.info(
        "invoking_main_agent",
        query=query[:50],
        num_documents=len(sub_agent_results)
    )

    # 构建提示词（同上）
    prompt = f"""用户问题: {query}

我已经分析了 {len(sub_agent_results)} 个相关文档，以下是每个文档的分析结果：

"""

    for idx, result in enumerate(sub_agent_results, 1):
        doc_name = result.get("document_name", "未知文档")
        answer = result.get("answer", "无内容")
        has_info = result.get("has_relevant_info", False)

        if has_info:
            prompt += f"""
## 文档 {idx}: {doc_name}

{answer}

---

"""

    prompt += """
请基于以上文档的分析结果，综合回答用户的问题。
"""

    try:
        result = await agent.invoke_async(prompt)

        # 提取回答
        answer_text = ""
        if hasattr(result, 'output'):
            if isinstance(result.output, str):
                answer_text = result.output
            elif isinstance(result.output, dict):
                answer_text = result.output.get('text', '')
        else:
            answer_text = str(result)

        # Token统计
        token_usage = {}
        if hasattr(result, 'metrics') and result.metrics:
            usage = result.metrics.accumulated_usage
            token_usage = {
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0)
            }

        logger.info(
            "main_agent_completed",
            answer_length=len(answer_text),
            total_tokens=token_usage.get("total_tokens", 0)
        )

        return {
            "answer": answer_text,
            "token_usage": token_usage
        }

    except Exception as e:
        logger.error(
            "main_agent_failed",
            error=str(e),
            exc_info=True
        )

        return {
            "answer": f"生成答案时出错: {str(e)}",
            "token_usage": {}
        }
