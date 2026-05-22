from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "course-orchestrator"
    temporal_host: str = "localhost:7233"
    course_service_url: str = "http://localhost:8002"
    kafka_bootstrap_servers: str = "127.0.0.1:9092"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()