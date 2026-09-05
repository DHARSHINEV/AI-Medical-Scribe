from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MediScribe"
    environment: str = "development"
    database_url: str
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "uploads"
    max_audio_size_mb: int = 50

    class Config:
        env_file = ".env"


settings = Settings()