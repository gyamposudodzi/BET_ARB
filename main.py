#!/usr/bin/env python3
import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime, timedelta
import platform
import signal
import json
        
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
from config.settings import settings
from core.rate_limiter import RateLimiter

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
        self.shutdown_event = asyncio.Event()
        self.rate_limiter = RateLimiter()
        
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
            self.telegram_bot.set_status_provider(self.get_system_status)
            if await self.telegram_bot.initialize():
                await self._send_startup_message()
                logger.info("Telegram bot connected")
        except Exception as e:
            logger.error(f"Telegram bot initialization failed: {e}")
            self.telegram_bot = None
    
    async def get_system_status(self):
        """Callback to provide system status to Telegram bot"""
        from database.session import get_db_stats
        
        # Get DB stats
        db_stats = await get_db_stats()
        
        return {
            "running": self.is_running,
            "scans": self.scan_count,
            "opportunities": self.opportunities_found,
            "db_stats": db_stats
        }

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
                loop.add_signal_handler(sig, self.signal_handler)
        else:
            # Windows fallback
            signal.signal(signal.SIGINT, lambda s, f: self.signal_handler('SIGINT'))
        
        logger.info(f"🔍 Starting scanning (interval: {settings.SCAN_INTERVAL}s)")
        
        try:
            while self.is_running:
                await self.scan_cycle()
                await asyncio.sleep(settings.SCAN_INTERVAL)
                
        except asyncio.CancelledError:
            logger.info("Scanning cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.shutdown()
    
    def signal_handler(self, signame=None):
        """Handle termination signals - called from signal handlers"""
        logger.info(f"Received signal {signame or 'SIGINT'}, shutting down...")
        self.is_running = False
    
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
                
                # Check rate limits before starting a cycle
                if self.rate_limiter.is_quota_exhausted:
                    logger.warning("🛑 API quota exhausted. Stopping scan cycle.")
                    return
                
                # Scan each sport
                for sport in sports:
                    await self.scan_sport(sport, crud)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Update sport last scan time
                for sport in sports:
                    await crud.update_sport_last_scan(sport.id)
                
                # Log stats every 10 scans
                if self.scan_count % 10 == 0:
                    stats = await crud.get_stats()
                    logger.info(f"📈 Scan #{self.scan_count}: {stats['opportunities_today']} opportunities today")
                
                break
                
        except Exception as e:
            logger.error(f"Scan cycle error: {e}")
    
    async def scan_sport(self, sport, crud):
        """Scan a specific sport for opportunities"""
        sport_key = sport.key
        logger.debug(f"Scanning {sport_key}...")
        
        try:
            # Fetch odds
            if hasattr(self.data_collector, 'get_odds') and settings.THE_ODDS_API_KEY:
                odds_data = await self.data_collector.get_odds(sport_key)
                # TODO: Update rate limiter with headers once odds_api.py is updated
                # self.rate_limiter.update_from_headers(response_headers)
            else:
                odds_data = self.data_collector.get_test_data(sport_key)
            
            if not odds_data:
                logger.debug(f"No data for {sport_key}")
                return

            # Persist the fetched data to the database
            await crud.process_and_store_market_data(sport.id, odds_data)
            
            # Detect arbitrage opportunities
            opportunities = await self.detector.process_api_data(odds_data)
            
            # Process detected opportunities
            for opportunity in opportunities:
                if opportunity.profit_percentage >= settings.MIN_PROFIT_THRESHOLD:
                    await self.handle_opportunity(opportunity, crud, sport.id)
            
            logger.debug(f"Scanned {sport_key}: {len(opportunities)} opportunities found")
            
        except Exception as e:
            logger.error(f"Error scanning {sport_key}: {e}")
    
    async def handle_opportunity(self, opportunity, crud, sport_id):
        """Handle a detected arbitrage opportunity"""
        
        # Get the internal event ID from the external ID
        db_event = await crud.get_event_by_external_id(sport_id, opportunity.event_id)
        if not db_event:
            logger.error(f"Could not find event with external ID {opportunity.event_id} for an opportunity.")
            return

        self.opportunities_found += 1
        
        # Save to database
        db_opportunity = await crud.create_opportunity({
            "event_id": db_event.id, # Use the internal ID
            "sport_key": opportunity.sport_key,
            "market_type": opportunity.market_type,
            "profit_percentage": opportunity.profit_percentage,
            "total_investment": opportunity.total_investment,
            "guaranteed_return": opportunity.guaranteed_return,
            "stake_allocations": opportunity.stake_allocations,
            "expiry_time": datetime.utcnow() + timedelta(seconds=settings.OPPORTUNITY_TIMEOUT),
            "status": "detected"
        })
        
        # Send alert
        if self.telegram_bot:
            # We need to update the opportunity object with the internal event ID if it's used in the alert
            opportunity.event_id = db_event.id
            await self.telegram_bot.send_opportunity_alert(opportunity)
            
            # Also log to database
            await crud.create_alert(
                level="info",
                category="opportunity",
                message=f"Arbitrage opportunity: {opportunity.profit_percentage}% profit",
                data=opportunity.to_dict()
            )
        
        logger.info(f"🎯 Opportunity #{self.opportunities_found} [DB:{db_opportunity.id}]: {opportunity.profit_percentage}% profit on event {db_event.home_team} vs {db_event.away_team}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        if not self.is_running and hasattr(self, '_shutting_down'):
            return
        
        self.is_running = False
        self._shutting_down = True
        
        logger.info("🛑 Shutting down...")
        
        try:
            # Send shutdown message first (before closing connection)
            if hasattr(self, 'telegram_bot') and self.telegram_bot and self.telegram_bot.bot:
                try:
                    await self.telegram_bot.send_system_alert(
                        f"🛑 Bot stopped\nTotal scans: {self.scan_count}\nOpportunities found: {self.opportunities_found}",
                        "info"
                    )
                except Exception as e:
                    logger.error(f"Could not send shutdown message: {e}")
        
        finally:
            # Close connections (always execute)
            try:
                if hasattr(self, 'data_collector'):
                    await self.data_collector.close()
            except Exception as e:
                logger.error(f"Error closing data collector: {e}")
            
            try:
                if hasattr(self, 'telegram_bot') and self.telegram_bot:
                    await self.telegram_bot.close()
            except Exception as e:
                logger.error(f"Error closing Telegram bot: {e}")
            
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