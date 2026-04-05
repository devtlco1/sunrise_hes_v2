from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://hes:hes@localhost:5432/hes"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    tcp_ingress_host: str = "0.0.0.0"
    tcp_ingress_port: int = 8766
    tcp_ingress_enabled: bool = True

    online_window_seconds: int = 900


settings = Settings()
