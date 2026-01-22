#!/usr/bin/env python3
import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime
import platform
import signal
        
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
from config.settings import settings

# Remove default logger
logger.remove()

# Add file logger
logger.add(
    settings.LOG_DIR / "arbitrage.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)

# Add console logger
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO"
)

class ArbitrageBot:
    def __init__(self):
        self.is_running = False
        self.scan_count = 0
        self.opportunities_found = 0
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Starting Arbitrage Bot")
        logger.info(f"📁 Database: {settings.DATABASE_URL}")
        
        # Initialize components
        await self._init_database()
        await self._init_telegram()
        await self._init_data_collector()
        await self._init_detector()
        
        logger.info("✅ Initialization complete")
    
    async def _init_database(self):
        """Initialize database"""
        try:
            from database.session import init_db, get_db_stats
            
            # Check if database exists
            db_path = settings.DATA_DIR / "arbitrage.db"
            if not db_path.exists():
                logger.info("Creating new database...")
                await init_db()
            
            stats = await get_db_stats()
            logger.info(f"📊 Database ready: {stats.get('bookmakers', 0)} bookmakers, {stats.get('sports', 0)} sports")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _init_telegram(self):
        """Initialize Telegram bot"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not set - alerts disabled")
            self.telegram_bot = None
            return
        
        try:
            from alerts.telegram_bot import TelegramAlertBot
            self.telegram_bot = TelegramAlertBot()
            if await self.telegram_bot.initialize():
                await self._send_startup_message()
        except Exception as e:
            logger.error(f"Telegram bot initialization failed: {e}")
            self.telegram_bot = None
    
    async def _send_startup_message(self):
        """Send startup message to Telegram"""
        if self.telegram_bot:
            await self.telegram_bot.send_system_alert(
                "🤖 Arbitrage Bot Started!\n"
                f"Minimum profit: {settings.MIN_PROFIT_THRESHOLD}%\n"
                f"Scan interval: {settings.SCAN_INTERVAL}s",
                "info"
            )
    
    async def _init_data_collector(self):
        """Initialize data collector"""
        from data_collection.odds_api import TheOddsAPI
        self.data_collector = TheOddsAPI()
        
        if settings.THE_ODDS_API_KEY:
            if await self.data_collector.initialize():
                logger.info("📡 Odds API connected")
            else:
                logger.warning("⚠️ Using test data (API not available)")
        else:
            logger.warning("⚠️ Using test data (API key not configured)")
    
    async def _init_detector(self):
        """Initialize arbitrage detector"""
        from core.detector import ArbitrageDetector
        self.detector = ArbitrageDetector()
        logger.info("🔍 Arbitrage detector ready")
    
    async def run(self):
        """Main application loop"""
        self.is_running = True
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        

        if platform.system() != "Windows":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda sig=sig: asyncio.create_task(self.shutdown())
                )
        else:
            # Windows fallback: Ctrl+C handling
            try:
                signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.shutdown()))
            except Exception:
                pass
        
        logger.info(f"🔍 Starting scanning (interval: {settings.SCAN_INTERVAL}s)")
        
        try:
            while self.is_running:
                await self.scan_cycle()
                await asyncio.sleep(settings.SCAN_INTERVAL)
                
        except asyncio.CancelledError:
            logger.info("Scanning cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await self.shutdown()
    
    async def scan_cycle(self):
        """Single scan cycle"""
        self.scan_count += 1
        
        try:
            from database.session import get_session
            from database.crud import CRUD
            
            async for session in get_session():
                crud = CRUD(session)
                # Get active sports
                sports = await crud.get_active_sports()
                
                if not sports:
                    logger.warning("No active sports configured")
                    return
                
                # Scan each sport
                for sport in sports[:3]:  # Limit to 3 sports for now
                    await self.scan_sport(sport.key, crud)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Update sport last scan time
                for sport in sports[:3]:
                    await crud.update_sport_last_scan(sport.id)
                
                # Log stats every 10 scans
                if self.scan_count % 10 == 0:
                    stats = await crud.get_stats()
                    logger.info(f"📈 Scan #{self.scan_count}: {stats['opportunities_today']} opportunities today")
                
                break
                
        except Exception as e:
            logger.error(f"Scan cycle error: {e}")
    
    async def scan_sport(self, sport_key: str, crud):
        """Scan a specific sport for opportunities"""
        logger.debug(f"Scanning {sport_key}...")
        
        try:
            # Fetch odds
            if hasattr(self.data_collector, 'get_odds') and settings.THE_ODDS_API_KEY:
                odds_data = await self.data_collector.get_odds(sport_key)
            else:
                odds_data = self.data_collector.get_test_data(sport_key)
            
            if not odds_data:
                logger.debug(f"No data for {sport_key}")
                return
            
            # Detect arbitrage opportunities
            opportunities = await self.detector.process_api_data(odds_data)
            
            # Process detected opportunities
            for opportunity in opportunities:
                if opportunity.profit_percentage >= settings.MIN_PROFIT_THRESHOLD:
                    await self.handle_opportunity(opportunity, crud)
            
            logger.debug(f"Scanned {sport_key}: {len(opportunities)} opportunities found")
            
        except Exception as e:
            logger.error(f"Error scanning {sport_key}: {e}")
    
    async def handle_opportunity(self, opportunity, crud):
        """Handle a detected arbitrage opportunity"""
        self.opportunities_found += 1
        
        # Save to database
        db_opportunity = await crud.create_opportunity({
            "event_id": opportunity.event_id,
            "sport_key": opportunity.sport_key,
            "market_type": opportunity.market_type,
            "profit_percentage": opportunity.profit_percentage,
            "total_investment": opportunity.total_investment,
            "guaranteed_return": opportunity.guaranteed_return,
            "stake_allocations": opportunity.stake_allocations,
            "expiry_time": datetime.utcnow().timestamp() + settings.OPPORTUNITY_TIMEOUT,
            "status": "detected"
        })
        
        # Send alert
        if self.telegram_bot:
            await self.telegram_bot.send_opportunity_alert(opportunity)
            
            # Also log to database
            await crud.create_alert(
                level="info",
                category="opportunity",
                message=f"Arbitrage opportunity: {opportunity.profit_percentage}% profit",
                data=opportunity.to_dict()
            )
        
        logger.info(f"🎯 Opportunity #{self.opportunities_found}: {opportunity.profit_percentage}% profit")
    
    async def shutdown(self):
        """Graceful shutdown"""
        if not self.is_running:
            return
        
        logger.info("🛑 Shutting down...")
        self.is_running = False
        
        # Close connections
        if hasattr(self, 'data_collector'):
            await self.data_collector.close()
        
        if hasattr(self, 'telegram_bot') and self.telegram_bot:
            await self.telegram_bot.close()
        
        # Send shutdown message
        if hasattr(self, 'telegram_bot') and self.telegram_bot:
            await self.telegram_bot.send_system_alert(
                f"🛑 Bot stopped\nTotal scans: {self.scan_count}\nOpportunities found: {self.opportunities_found}",
                "info"
            )
        
        logger.info(f"📊 Final stats: {self.scan_count} scans, {self.opportunities_found} opportunities")
        logger.info("👋 Shutdown complete")

async def main():
    """Main entry point"""
    bot = ArbitrageBot()
    
    try:
        await bot.initialize()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    # Check if running in interactive mode
    if hasattr(sys, 'ps1'):
        print("Running in interactive mode. Use: await main()")
    else:
        asyncio.run(main())