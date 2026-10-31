from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "GeMAI API"

    # File uploads
    upload_dir: Path = BASE_DIR / "uploads"
    max_file_size_mb: int = 10
    max_pdf_pages: int = 50
    allowed_extensions: tuple[str, ...] = (".pdf",)

    # Storage
    database_url: str = f"sqlite:///{BASE_DIR / 'gemai.db'}"

    # LLM (read from .env, never hardcode)
    llm_api_key: str | None = None

    # Allow Member 1's React dev server to call the API
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)