from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_name: str = "Stock Market API"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "localhost"
    port: int = 8000
    
    # CORS settings
    allowed_origins: List[str] = ["*"]
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]
    
    # Threading settings
    max_workers: int = 10
    timeout_seconds: int = 30
    
    # Cache settings
    cache_timeout: int = 300  # 5 minutes
    
    
    SECRET_TOTP: str = Field(..., description="TOTP secret for 2FA")
    USER: str = Field(..., description="Shoonya username")
    U_PWD: str = Field(..., description="Shoonya password")
    VC: str = Field(..., description="Shoonya vendor code")
    APP_KEY: str = Field(..., description="Shoonya app key")
    IMET: str = Field(..., description="Device IMEI")
    DHAN_ACCESS_TOKEN: str = Field(..., description="Dhan access token")
    CLIENT_ID: str = Field(..., description="Dhan client ID")
    
    class Config:
        env_file = ".env"
        extra ="allow"

settings = Settings()
