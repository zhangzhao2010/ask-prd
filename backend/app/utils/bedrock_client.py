"""
AWS Bedrock客户端工具类
使用Strands Agent框架集成
"""
from typing import List, Optional
import boto3
from strands.models import BedrockModel
from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import BedrockAPIError

logger = get_logger(__name__)


class BedrockClient:
    """Bedrock客户端封装"""

    def __init__(self):
        """初始化Bedrock客户端"""
        try:
            # 创建boto session
            self.boto_session = boto3.Session(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.bedrock_region
            )

            # 创建Bedrock Runtime客户端（用于直接调用embedding）
            self.runtime_client = self.boto_session.client(
                'bedrock-runtime',
                region_name=settings.bedrock_region
            )

            logger.info(
                "bedrock_client_initialized",
                region=settings.bedrock_region,
                generation_model=settings.generation_model_id,
                embedding_model=settings.embedding_model_id
            )

        except Exception as e:
            logger.error("bedrock_init_failed", error=str(e))
            raise BedrockAPIError({"error": str(e)})

    def get_generation_model(
        self,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        streaming: bool = True
    ) -> BedrockModel:
        """
        获取生成模型（Claude Sonnet 4.5）

        Args:
            temperature: 温度参数
            max_tokens: 最大生成token数
            streaming: 是否启用流式输出

        Returns:
            BedrockModel实例
        """
        try:
            model = BedrockModel(
                model_id=settings.generation_model_id,
                region_name=settings.bedrock_region,
                boto_session=self.boto_session,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming
            )

            logger.debug(
                "generation_model_created",
                model_id=settings.generation_model_id,
                temperature=temperature,
                streaming=streaming
            )

            return model

        except Exception as e:
            logger.error("create_generation_model_failed", error=str(e))
            raise BedrockAPIError({"error": str(e), "model_id": settings.generation_model_id})

    def generate_embeddings(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[List[float]]:
        """
        生成文本向量（Titan Embeddings V2）

        Args:
            texts: 文本列表
            normalize: 是否归一化向量

        Returns:
            向量列表
        """
        try:
            embeddings = []

            for text in texts:
                # 调用Bedrock Titan Embeddings V2
                response = self.runtime_client.invoke_model(
                    modelId=settings.embedding_model_id,
                    body={
                        "inputText": text,
                        "dimensions": 1024,
                        "normalize": normalize
                    },
                    contentType="application/json",
                    accept="application/json"
                )

                # 解析响应
                import json
                result = json.loads(response['body'].read())
                embedding = result.get('embedding', [])
                embeddings.append(embedding)

            logger.debug(
                "embeddings_generated",
                count=len(texts),
                dimension=len(embeddings[0]) if embeddings else 0
            )

            return embeddings

        except Exception as e:
            logger.error("generate_embeddings_failed", error=str(e), text_count=len(texts))
            raise BedrockAPIError({
                "error": str(e),
                "model_id": settings.embedding_model_id,
                "text_count": len(texts)
            })

    def generate_embedding(self, text: str, normalize: bool = True) -> List[float]:
        """
        生成单个文本的向量

        Args:
            text: 文本
            normalize: 是否归一化向量

        Returns:
            向量
        """
        embeddings = self.generate_embeddings([text], normalize)
        return embeddings[0] if embeddings else []

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 25,
        normalize: bool = True
    ) -> List[List[float]]:
        """
        批量生成向量（自动分批）

        Args:
            texts: 文本列表
            batch_size: 批次大小
            normalize: 是否归一化向量

        Returns:
            向量列表
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.generate_embeddings(batch, normalize)
            all_embeddings.extend(embeddings)

            logger.debug(
                "batch_embeddings_generated",
                batch=i // batch_size + 1,
                batch_size=len(batch)
            )

        return all_embeddings

    def count_tokens(self, text: str) -> int:
        """
        估算token数量（使用tiktoken）

        Args:
            text: 文本

        Returns:
            token数量
        """
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")  # Claude使用的编码
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning("token_count_failed", error=str(e))
            # 简单估算：1 token ≈ 4字符
            return len(text) // 4

    def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        media_type: str = "image/png",
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> str:
        """
        使用Claude Vision API分析图片

        Args:
            image_base64: 图片的base64编码
            prompt: 分析提示词
            media_type: 图片MIME类型（image/png, image/jpeg等）
            max_tokens: 最大生成token数
            temperature: 温度参数

        Returns:
            分析结果文本
        """
        try:
            import json

            # 构建请求体
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }

            # 调用Bedrock API
            response = self.runtime_client.invoke_model(
                modelId=settings.generation_model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            # 解析响应
            response_body = json.loads(response["body"].read())
            result_text = response_body["content"][0]["text"]

            logger.debug(
                "image_analysis_completed",
                prompt_length=len(prompt),
                result_length=len(result_text)
            )

            return result_text.strip()

        except Exception as e:
            logger.error("image_analysis_failed", error=str(e), exc_info=True)
            raise BedrockAPIError({
                "error": str(e),
                "model_id": settings.generation_model_id,
                "operation": "analyze_image"
            })


# 全局Bedrock客户端实例
bedrock_client = BedrockClient()
