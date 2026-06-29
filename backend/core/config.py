"""
core/config.py
--------------
Centralised settings loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    # Transient-failure retry policy for Groq calls (rate limits, 5xx, timeouts).
    groq_max_retries: int = 3
    groq_retry_base_delay: float = 1.0  # seconds; doubled each attempt

    # Processing limits
    max_cvs_per_batch: int = 50
    top_n_candidates: int = 10
    processing_timeout_seconds: int = 120

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
