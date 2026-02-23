from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import io
import logging
import uuid
from datetime import timedelta

logger = logging.getLogger(__name__)


class MinioService:
    """Service para armazenamento de arquivos no MinIO"""

    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "closefy",
        secret_key: str = "Closefy2026!!",
        secure: bool = False
    ):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.default_bucket = "closefy-knowledge"

    def ensure_bucket(self, bucket_name: str = None) -> bool:
        """Garante que o bucket existe"""
        bucket = bucket_name or self.default_bucket
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Bucket '{bucket}' criado")
            return True
        except S3Error as e:
            logger.error(f"Erro ao criar bucket: {e}")
            return False

    def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        bucket_name: str = None,
        folder: str = None
    ) -> Optional[str]:
        """
        Faz upload de arquivo para o MinIO
        Retorna o object_name (caminho no bucket)
        """
        bucket = bucket_name or self.default_bucket
        self.ensure_bucket(bucket)

        # Gerar nome único
        unique_id = str(uuid.uuid4())[:8]
        if folder:
            object_name = f"{folder}/{unique_id}_{filename}"
        else:
            object_name = f"{unique_id}_{filename}"

        try:
            # Obter tamanho do arquivo
            file_data.seek(0, 2)  # Move para o final
            file_size = file_data.tell()
            file_data.seek(0)  # Volta para o início

            self.client.put_object(
                bucket,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )
            logger.info(f"Arquivo '{object_name}' uploaded para bucket '{bucket}'")
            return object_name

        except S3Error as e:
            logger.error(f"Erro ao fazer upload: {e}")
            return None

    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        bucket_name: str = None,
        folder: str = None
    ) -> Optional[str]:
        """Faz upload de bytes para o MinIO"""
        return self.upload_file(
            io.BytesIO(data),
            filename,
            content_type,
            bucket_name,
            folder
        )

    def get_file(self, object_name: str, bucket_name: str = None) -> Optional[bytes]:
        """Baixa arquivo do MinIO"""
        bucket = bucket_name or self.default_bucket
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Erro ao baixar arquivo: {e}")
            return None

    def get_presigned_url(
        self,
        object_name: str,
        bucket_name: str = None,
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """Gera URL pré-assinada para acesso temporário"""
        bucket = bucket_name or self.default_bucket
        try:
            url = self.client.presigned_get_object(bucket, object_name, expires=expires)
            return url
        except S3Error as e:
            logger.error(f"Erro ao gerar URL: {e}")
            return None

    def delete_file(self, object_name: str, bucket_name: str = None) -> bool:
        """Remove arquivo do MinIO"""
        bucket = bucket_name or self.default_bucket
        try:
            self.client.remove_object(bucket, object_name)
            logger.info(f"Arquivo '{object_name}' removido do bucket '{bucket}'")
            return True
        except S3Error as e:
            logger.error(f"Erro ao remover arquivo: {e}")
            return False

    def list_files(self, prefix: str = "", bucket_name: str = None) -> list:
        """Lista arquivos no bucket"""
        bucket = bucket_name or self.default_bucket
        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Erro ao listar arquivos: {e}")
            return []
