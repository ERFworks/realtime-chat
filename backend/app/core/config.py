from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URL: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str
    MINIO_USE_SSL: bool = False

    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWD_IMAGE_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}

    model_config = SettingsConfigDict(env_file=".env")



settings = Settings()