from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "enrollment-service"
    database_url: str
    debug: bool = True
    course_service_url: str
    jwt_secret: str
    kafka_bootstrap_servers: str = "localhost:9092"
    temporal_host: str = "localhost:7233"
    temporal_task_queue: str = "enrollment-task-queue"
    temporal_workflow_timeout: int = 1800
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()