from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "enrollment-orchestrator"
    temporal_host: str = "localhost:7233"
    temporal_task_queue: str = "enrollment-task-queue"
    course_service_url: str = "http://localhost:8002"
    enrollment_service_url: str = "http://localhost:8003"
    kafka_bootstrap_servers: str = "127.0.0.1:9092"

    # Retry policy
    temporal_max_retries: int = 3
    temporal_initial_retry_interval: int = 2  
    temporal_max_retry_interval: int = 60     

    # Timeouts
    temporal_activity_timeout: int = 30        
    temporal_workflow_timeout: int = 1800      
    temporal_http_timeout: float = 10.0        

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
