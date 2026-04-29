import os
from pathlib import Path

from dotenv import load_dotenv


# 兼容当前项目结构：优先读取 app/.env，同时也支持根目录 .env。
APP_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

if APP_ENV_PATH.exists():
    load_dotenv(APP_ENV_PATH)
elif ROOT_ENV_PATH.exists():
    load_dotenv(ROOT_ENV_PATH)


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AI Resume Matcher")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://appuser:AppPass123%21@host.docker.internal:3306/ai_resume_matcher",
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


settings = Settings()
