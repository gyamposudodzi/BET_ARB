#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    print(f"🔧 {description}...")
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def main():
    print("🚀 Arbitrage Bot Setup (SQLite Edition)")
    print("=" * 50)
    
    # Create necessary directories
    directories = ["data", "logs", "config", "core", "database", "alerts", "data_collection"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    # Create virtual environment
    if not Path("venv").exists():
        run_command("python3 -m venv venv", "Creating virtual environment")
    
    # Activate venv and install packages
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate && "
    else:
        activate_cmd = "source venv/bin/activate && "
    
    # Install requirements
    run_command(f"{activate_cmd}pip install --upgrade pip", "Upgrading pip")
    run_command(f"{activate_cmd}pip install -r requirements.txt", "Installing requirements")
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        with open(".env", "w") as f:
            f.write("""# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# The Odds API (get from https://the-odds-api.com/)
THE_ODDS_API_KEY=your_api_key_here

# Trading Parameters
MIN_PROFIT_THRESHOLD=0.5
MAX_BET_PERCENTAGE=2.0
MIN_STAKE=10.0
MAX_STAKE=1000.0

# Timing
SCAN_INTERVAL=30
OPPORTUNITY_TIMEOUT=60
""")
        print("✅ Created .env file - Please edit with your credentials")
    
    # Create bookmakers config
    if not Path("config/bookmakers.yaml").exists():
        with open("config/bookmakers.yaml", "w") as f:
            f.write("""bookmakers:
  pinnacle:
    display_name: "Pinnacle"
    api_available: false
    scrape_url: "https://www.pinnacle.com"
    priority: 1
    
  bet365:
    display_name: "Bet365"
    api_available: false
    scrape_url: "https://www.bet365.com"
    priority: 2
    
  draftkings:
    display_name: "DraftKings"
    api_available: false
    scrape_url: "https://www.draftkings.com"
    priority: 3

sports:
  - key: "basketball_nba"
    name: "NBA Basketball"
    priority: 1
    markets: ["h2h", "spreads", "totals"]
    
  - key: "soccer_epl"
    name: "English Premier League"
    priority: 2
    markets: ["h2h", "spreads", "totals"]
    
  - key: "americanfootball_nfl"
    name: "NFL Football"
    priority: 3
    markets: ["h2h", "spreads", "totals"]
""")
        print("✅ Created bookmakers configuration")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python init_db.py")
    print("3. Run: python main.py")
    print("\nGet API keys:")
    print("  • The Odds API: https://the-odds-api.com/")
    print("  • Telegram Bot: https://t.me/BotFather")

if __name__ == "__main__":
    main()