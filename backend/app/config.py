from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    storage_path: str = "./storage/contracts"

    class Config:
        env_file = ".env"


settings = Settings()
