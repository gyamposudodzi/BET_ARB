import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "BET_ARB Bot"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database (SQLite)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/bet_arb.db"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    
    # The Odds API
    THE_ODDS_API_KEY: Optional[str] = os.getenv("THE_ODDS_API_KEY")
    ODDS_API_REGIONS: str = os.getenv("ODDS_API_REGIONS", "us,uk,eu,au") # Regions to scan
    
    # Trading Parameters
    MIN_PROFIT_THRESHOLD: float = float(os.getenv("MIN_PROFIT_THRESHOLD", "0.5"))
    MAX_PROFIT_THRESHOLD: float = float(os.getenv("MAX_PROFIT_THRESHOLD", "30.0")) # Sanity check to filter bad data/outrights
    MAX_BET_PERCENTAGE: float = float(os.getenv("MAX_BET_PERCENTAGE", "2.0"))
    MIN_STAKE: float = float(os.getenv("MIN_STAKE", "10.0"))
    MAX_STAKE: float = float(os.getenv("MAX_STAKE", "1000.0"))
    
    # Value Betting (EV+)
    SHARP_BOOKMAKER: str = os.getenv("SHARP_BOOKMAKER", "pinnacle") # Reference for "True" probability
    MIN_EV_THRESHOLD: float = float(os.getenv("MIN_EV_THRESHOLD", "2.0")) # Minimum Value %
    
    # Anti-Detection
    ROUND_STAKES: bool = True
    ROUNDING_BASE: int = 5
    
    # Timing
    SCAN_INTERVAL: int = int(os.getenv("SCAN_INTERVAL", "30"))
    OPPORTUNITY_TIMEOUT: int = int(os.getenv("OPPORTUNITY_TIMEOUT", "60"))
    
    # Paths
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"
    
    class Config:
        env_file = ".env"

# Create instance
settings = Settings()

# Create directories
settings.DATA_DIR.mkdir(exist_ok=True)
settings.LOG_DIR.mkdir(exist_ok=True)