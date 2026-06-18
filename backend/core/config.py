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

    # Processing limits
    max_cvs_per_batch: int = 50
    top_n_candidates: int = 10
    processing_timeout_seconds: int = 120

    # How long a job's state (status, results, parsed CVs) is retained in the
    # in-memory store after its last activity, before being evicted. Prevents
    # unbounded memory growth on long-running servers. Default: 1 hour.
    job_retention_seconds: int = 3600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
