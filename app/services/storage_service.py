"""
Сервис хранения файлов через MinIO (S3-совместимый).
"""
from __future__ import annotations

import io
import logging
import uuid
from typing import BinaryIO

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    from minio import Minio  # type: ignore
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_USE_SSL,
    )
    # Создаём бакет если не существует
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
    return client


def upload_file(content: bytes, original_filename: str, content_type: str) -> str:
    """
    Загружает файл в MinIO, возвращает storage_key.
    """
    client = _get_client()
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "bin"
    key = f"docs/{uuid.uuid4().hex}.{ext}"

    client.put_object(
        settings.MINIO_BUCKET,
        key,
        io.BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    logger.info("Uploaded file to MinIO: %s", key)
    return key


def download_file(storage_key: str) -> bytes:
    """Скачивает файл из MinIO по ключу."""
    client = _get_client()
    resp = client.get_object(settings.MINIO_BUCKET, storage_key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def delete_file(storage_key: str) -> None:
    client = _get_client()
    client.remove_object(settings.MINIO_BUCKET, storage_key)
    logger.info("Deleted from MinIO: %s", storage_key)
