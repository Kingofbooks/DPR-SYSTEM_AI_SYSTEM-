import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    #Application settings
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    
    #Database settings
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE","sqlite")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")
    
    #Application settings
    APP_NAME: str = os.getenv("APP_NAME", "MyApp")
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() in ("true", "1", "t")
    
    #Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    #MCP settings
    MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")
    GIT_HUB_TOKEN: str = os.getenv("GIT_HUB_TOKEN", "")
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    
    #Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "jwtsecretkey")
    

config = Config()

