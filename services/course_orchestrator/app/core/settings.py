from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "course-orchestrator"
    temporal_host: str = "localhost:7233"
    temporal_task_queue: str = "course-task-queue"
    course_service_url: str = "http://localhost:8002"
    kafka_bootstrap_servers: str = "127.0.0.1:9092"

    # Retry policy
    temporal_max_retries: int = 3
    temporal_initial_retry_interval: int = 2 
    temporal_max_retry_interval: int = 60     
    temporal_compensation_max_retries: int = 5

    # Timeouts
    temporal_activity_timeout: int = 30       
    temporal_workflow_timeout: int = 1800      
    temporal_http_timeout: float = 10.0       

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()