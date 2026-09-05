from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MediScribe"
    environment: str = "development"
    database_url: str = "sqlite:///./mediscribe.db"
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:8000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:8000"
    )
    upload_dir: str = "uploads"
    max_audio_size_mb: int = 50

    # AI Configuration
    whisper_model: str = "tiny"
    whisper_language: str = "en"

    # Security Configuration
    secret_key: str = (
        "mediscribe-dev-secret-key-32-chars-minimum-for-testing"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()