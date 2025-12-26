from typing import Any, List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration settings.
    
    Loads values from environment variables or .env file.
    """
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Contri API"
    
    # SECURITY
    SECRET_KEY: str = Field(description="Secret key for JWT encoding")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # DATABASE
    DATABASE_URL: str = Field(description="PostgreSQL Connection URL")

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Social Login
    GOOGLE_CLIENT_ID: str | None = None
    APPLE_CLIENT_ID: str | None = None

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        """
        Parses comma-separated string of CORS origins into a list.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
