"""Almacenamiento de los PDF del expediente: sistema de archivos local o MinIO/S3."""
import os
from pathlib import Path
from typing import Protocol

from ..config import get_settings


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> str: ...
    def get(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, base: str):
        self.base = Path(base)

    def _ruta(self, key: str) -> Path:
        ruta = (self.base / key).resolve()
        if not str(ruta).startswith(str(self.base.resolve())):
            raise ValueError("Ruta fuera del almacenamiento")
        return ruta

    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        ruta = self._ruta(key)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._ruta(key).read_bytes()


class S3Storage:
    def __init__(self):
        import boto3
        from botocore.exceptions import ClientError

        s = get_settings()
        self.bucket = s.s3_bucket
        self.cliente = boto3.client(
            "s3", endpoint_url=s.s3_endpoint_url, aws_access_key_id=s.s3_access_key,
            aws_secret_access_key=s.s3_secret_key, region_name=s.s3_region)
        try:
            self.cliente.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.cliente.create_bucket(Bucket=self.bucket)

    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        self.cliente.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get(self, key: str) -> bytes:
        return self.cliente.get_object(Bucket=self.bucket, Key=key)["Body"].read()


_instancia: Storage | None = None


def get_storage() -> Storage:
    global _instancia
    if _instancia is None:
        s = get_settings()
        _instancia = S3Storage() if s.storage_backend == "s3" else LocalStorage(s.local_storage_path)
    return _instancia


def set_storage(st: Storage | None) -> None:  # pruebas
    global _instancia
    _instancia = st
