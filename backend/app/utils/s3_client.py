"""
AWS S3客户端工具类
"""
import os
from typing import Optional, BinaryIO
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logging import get_logger
from app.core.errors import S3UploadError

logger = get_logger(__name__)


class S3Client:
    """S3客户端封装"""

    def __init__(self):
        """初始化S3客户端"""
        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.client = session.client('s3')
        self.bucket = settings.s3_bucket

        logger.info("s3_client_initialized", bucket=self.bucket, region=settings.aws_region)

    def upload_file(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到S3

        Args:
            file_obj: 文件对象
            s3_key: S3路径
            content_type: Content-Type

        Returns:
            S3完整路径

        Raises:
            S3UploadError: 上传失败
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info("file_uploaded_to_s3", s3_key=s3_key, bucket=self.bucket)
            return f"s3://{self.bucket}/{s3_key}"

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_upload_failed", s3_key=s3_key, error=error_msg)
            raise S3UploadError(
                s3_key=s3_key,
                details={"error": error_msg}
            )

    def upload_file_from_path(
        self,
        local_path: str,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        从本地路径上传文件到S3

        Args:
            local_path: 本地文件路径
            s3_key: S3路径
            content_type: Content-Type

        Returns:
            S3完整路径
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.client.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info("file_uploaded_from_path", local_path=local_path, s3_key=s3_key)
            return f"s3://{self.bucket}/{s3_key}"

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_upload_from_path_failed", s3_key=s3_key, error=error_msg)
            raise S3UploadError(
                s3_key=s3_key,
                details={"error": error_msg, "local_path": local_path}
            )

    def download_file(self, s3_key: str, local_path: str) -> str:
        """
        从S3下载文件到本地

        Args:
            s3_key: S3路径
            local_path: 本地保存路径

        Returns:
            本地文件路径
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            self.client.download_file(
                self.bucket,
                s3_key,
                local_path
            )

            logger.info("file_downloaded_from_s3", s3_key=s3_key, local_path=local_path)
            return local_path

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_download_failed", s3_key=s3_key, error=error_msg)
            raise Exception(f"S3下载失败: {error_msg}")

    def download_file_bytes(self, s3_key: str) -> bytes:
        """
        从S3下载文件内容（返回bytes）

        Args:
            s3_key: S3路径

        Returns:
            文件二进制内容
        """
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return response['Body'].read()

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_download_bytes_failed", s3_key=s3_key, error=error_msg)
            raise Exception(f"S3下载失败: {error_msg}")

    def delete_file(self, s3_key: str) -> bool:
        """
        删除S3文件

        Args:
            s3_key: S3路径

        Returns:
            是否删除成功
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            logger.info("file_deleted_from_s3", s3_key=s3_key)
            return True

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_delete_failed", s3_key=s3_key, error=error_msg)
            return False

    def delete_prefix(self, prefix: str) -> int:
        """
        删除S3前缀下的所有文件

        Args:
            prefix: S3路径前缀

        Returns:
            删除的文件数量
        """
        try:
            # 列出所有文件
            objects = self.list_objects(prefix)

            if not objects:
                return 0

            # 批量删除
            delete_keys = [{'Key': obj} for obj in objects]
            response = self.client.delete_objects(
                Bucket=self.bucket,
                Delete={'Objects': delete_keys}
            )

            deleted_count = len(response.get('Deleted', []))
            logger.info("s3_prefix_deleted", prefix=prefix, count=deleted_count)
            return deleted_count

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_delete_prefix_failed", prefix=prefix, error=error_msg)
            return 0

    def list_objects(self, prefix: str, max_keys: int = 1000) -> list:
        """
        列出S3前缀下的所有对象

        Args:
            prefix: S3路径前缀
            max_keys: 最大返回数量

        Returns:
            对象key列表
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            return [obj['Key'] for obj in response['Contents']]

        except ClientError as e:
            error_msg = str(e)
            logger.error("s3_list_failed", prefix=prefix, error=error_msg)
            return []

    def file_exists(self, s3_key: str) -> bool:
        """
        检查S3文件是否存在

        Args:
            s3_key: S3路径

        Returns:
            文件是否存在
        """
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return True
        except ClientError:
            return False

    def get_file_size(self, s3_key: str) -> Optional[int]:
        """
        获取S3文件大小

        Args:
            s3_key: S3路径

        Returns:
            文件大小（字节），不存在返回None
        """
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return response['ContentLength']
        except ClientError:
            return None


# 全局S3客户端实例
s3_client = S3Client()
