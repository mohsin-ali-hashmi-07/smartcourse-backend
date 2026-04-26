from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "enrollment-service"
    database_url: str
    debug: bool = True
    course_service_url: str
    jwt_secret: str
    kafka_bootstrap_servers: str = "localhost:9092"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()