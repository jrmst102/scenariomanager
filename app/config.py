"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Core
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "dev-session-secret-change-me")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    PORT: int = int(os.getenv("PORT", "8000"))
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # DigitalOcean Spaces
    SPACES_ENDPOINT: str = os.getenv("SPACES_ENDPOINT", "")
    SPACES_KEY: str = os.getenv("SPACES_KEY", "")
    SPACES_SECRET: str = os.getenv("SPACES_SECRET", "")
    SPACES_BUCKET: str = os.getenv("SPACES_BUCKET", "")
    SPACES_REGION: str = os.getenv("SPACES_REGION", "")

    # OpenAI / LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_FALLBACK_MODEL: str = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT_MS: int = int(os.getenv("OPENAI_TIMEOUT_MS", "14000"))
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "0"))

    @property
    def use_spaces(self) -> bool:
        return bool(self.SPACES_ENDPOINT and self.SPACES_KEY and self.SPACES_SECRET and self.SPACES_BUCKET)

    @property
    def llm_available(self) -> bool:
        return bool(self.LLM_ENABLED and self.OPENAI_API_KEY)


settings = Settings()
