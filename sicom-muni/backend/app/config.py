"""Configuracion central (variables de entorno / archivo .env)."""
import base64
import hashlib
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg://sicom:sicom@localhost:5432/sicom"
    secret_key: str = "cambiar-esta-clave-en-produccion-minimo-32-caracteres"
    fernet_key: str = ""  # si vacio se deriva de secret_key
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cookie_secure: bool = False  # True en produccion (HTTPS)
    cookie_samesite: str = "strict"
    cors_origins: str = "http://localhost:3000"
    public_base_url: str = "http://localhost:3000"  # URL publica para los QR de verificacion

    max_failed_logins: int = 5
    lockout_minutes: int = 15

    storage_backend: str = "local"  # local | s3
    local_storage_path: str = "./storage"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "sicom-expedientes"
    s3_region: str = "us-east-1"

    smtp_host: str = ""  # vacio = las fichas de cotizacion se registran sin enviar correo
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "contrataciones@gam.local"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fernet_key_effective(self) -> bytes:
        if self.fernet_key:
            return self.fernet_key.encode()
        return base64.urlsafe_b64encode(hashlib.sha256(self.secret_key.encode()).digest())


@lru_cache
def get_settings() -> Settings:
    return Settings()
