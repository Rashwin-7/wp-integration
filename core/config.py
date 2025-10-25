import os
from typing import List, Optional
from decouple import config
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ==================== APPLICATION CONFIG ====================
    PROJECT_NAME: str = "SaaS WhatsApp Gateway"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = config("DEBUG", default=False, cast=bool)
    ENVIRONMENT: str = config("ENVIRONMENT", default="development")
    
    # ==================== DATABASE CONFIG ====================
    DATABASE_URL: str = config("DATABASE_URL")
    DB_POOL_SIZE: int = config("DB_POOL_SIZE", default=5, cast=int)
    DB_MAX_OVERFLOW: int = config("DB_MAX_OVERFLOW", default=10, cast=int)
    DB_ECHO: bool = config("DB_ECHO", default=False, cast=bool)
    
    # ==================== RABBITMQ CONFIG ====================
    RABBITMQ_URL: str = config("RABBITMQ_URL", default="amqp://guest:guest@localhost:5672/")
    RABBITMQ_HEARTBEAT: int = config("RABBITMQ_HEARTBEAT", default=600, cast=int)
    
    # ==================== WHATSAPP BUSINESS API CONFIG ====================
    WHATSAPP_PHONE_NUMBER_ID: str = config("WHATSAPP_PHONE_NUMBER_ID", default="")
    WHATSAPP_ACCESS_TOKEN: str = config("WHATSAPP_ACCESS_TOKEN", default="")
    WHATSAPP_API_URL: str = config("WHATSAPP_API_URL", default="https://graph.facebook.com/v18.0")
    WHATSAPP_API_TIMEOUT: int = config("WHATSAPP_API_TIMEOUT", default=30, cast=int)
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = config("WHATSAPP_WEBHOOK_VERIFY_TOKEN", default="default_verify_token")
    
    # ==================== SECURITY CONFIG ====================
    SECRET_KEY: str = config("SECRET_KEY")
    API_KEY_HEADER: str = config("API_KEY_HEADER", default="X-API-Key")
    HMAC_SECRET: str = config("HMAC_SECRET")
    
    # Security - Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = config("RATE_LIMIT_PER_MINUTE", default=60, cast=int)
    RATE_LIMIT_PER_HOUR: int = config("RATE_LIMIT_PER_HOUR", default=1000, cast=int)
    
    # Security - API Key
    API_KEY_ROTATION_DAYS: int = config("API_KEY_ROTATION_DAYS", default=90, cast=int)
    
    # ==================== CORS CONFIG ====================
    ALLOWED_HOSTS: List[str] = config(
        "ALLOWED_HOSTS", 
        default="localhost,127.0.0.1,0.0.0.0", 
        cast=lambda v: [s.strip() for s in v.split(",")]
    )
    
    # ==================== LOGGING CONFIG ====================
    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
    LOG_FORMAT: str = config("LOG_FORMAT", default="json")  # json or console
    
    # ==================== PERFORMANCE CONFIG ====================
    MAX_MESSAGE_SIZE: int = config("MAX_MESSAGE_SIZE", default=4096, cast=int)  # 4KB max message size
    BACKGROUND_WORKER_COUNT: int = config("BACKGROUND_WORKER_COUNT", default=2, cast=int)
    
    # ==================== FEATURE FLAGS ====================
    ENABLE_RATE_LIMITING: bool = config("ENABLE_RATE_LIMITING", default=True, cast=bool)
    ENABLE_WEBHOOK_VERIFICATION: bool = config("ENABLE_WEBHOOK_VERIFICATION", default=True, cast=bool)
    ENABLE_MESSAGE_QUEUE: bool = config("ENABLE_MESSAGE_QUEUE", default=True, cast=bool)
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Dependency for getting settings"""
    return settings