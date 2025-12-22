from pydantic_settings import BaseSettings
import os

# Configuration settings that can be loaded from environment variables
class Settings(BaseSettings):
    # App Security
    SECRET_KEY: str
    UPLOAD_DIR: str
    FRONTEND_AUTH_CALLBACK_URL: str
    # Database
    DATABASE_URL: str

    # Google Auth
    GOOGLE_AUTH_CLIENT_ID: str
    GOOGLE_AUTH_CLIENT_SECRET: str
    
    # OpenAI
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure upload directory exists on startup
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)