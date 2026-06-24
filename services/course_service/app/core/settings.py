from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "course-service"
    database_url: str
    debug: bool = True
    jwt_secret: str
    redis_url: str = "redis://localhost:6379"
    kafka_bootstrap_servers: str = "localhost:9092"
    temporal_host: str = "localhost:7233"
    temporal_task_queue: str = "course-task-queue"
    temporal_workflow_timeout: int = 1800

    # MinIO / S3-compatible object storage
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "course-materials"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()