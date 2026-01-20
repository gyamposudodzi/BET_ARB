import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Database
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", 5432))
    db_name: str = os.getenv("DB_NAME", "arbitrage_bot")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "")
    
    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Settings
    min_arb_margin: float = float(os.getenv("MIN_ARB_MARGIN", 0.7))
    scan_interval_seconds: int = int(os.getenv("SCAN_INTERVAL_SECONDS", 30))
    simulation_mode: bool = os.getenv("BOOKMAKER_SIMULATION_MODE", "true").lower() == "true"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def postgres_url(self) -> str:
        """URL for connecting to default postgres database (for creating our DB)"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/postgres"
    
    def validate(self):
        """Validate critical configuration"""
        errors = []
        
        if not self.db_user:
            errors.append("DB_USER is not set")
        
        if not self.db_name:
            errors.append("DB_NAME is not set")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

# Create global settings instance
settings = Settings()