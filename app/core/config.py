from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "RoleChatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/role_chatbot.db"

    # Chroma
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Ollama
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Embedding
    EMBEDDING_MODEL_PATH: str = "./models/bge-small-zh-v1.5"
    RERANKER_MODEL_PATH: str = "./models/bge-reranker-base"
    
    # 安全
    SECRET_KEY: str = "this-is-a-test-for-my-secret-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局单例
settings = Settings()