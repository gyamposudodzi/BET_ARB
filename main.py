import asyncio
import logging
import sys
from datetime import datetime

from config import settings
from database import db
from odds_ingestion import odds_fetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('arbitrage_bot.log')
    ]
)

logger = logging.getLogger(__name__)

async def setup():
    """Initialize the system"""
    logger.info("🚀 Starting Arbitrage Bot Setup...")
    
    # Validate configuration
    try:
        settings.validate()
        logger.info("✅ Configuration validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return False
    
    # Connect to database
    try:
        await db.connect()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return False
    
    logger.info("✅ Setup completed successfully")
    return True

async def run_single_scan():
    """Run a single scan cycle"""
    logger.info("=" * 60)
    logger.info(f"🔍 Starting scan at {datetime.utcnow().isoformat()}")
    
    # 1. Fetch odds
    odds_data = await odds_fetcher.fetch_all()
    
    if not odds_data:
        logger.warning("No odds data fetched")
        return
    
    # 2. Store in database
    await db.insert_odds(odds_data)
    
    # 3. Log sample data
    logger.info(f"📊 Sample odds (first 3):")
    for odds in odds_data[:3]:
        logger.info(f"  {odds['bookmaker']}: {odds['event']} - {odds['market']} {odds['outcome']} @ {odds['odds']}")
    
    logger.info(f"✅ Scan completed. Processed {len(odds_data)} odds entries")

async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("🎯 SPORTS ARBITRAGE BOT - PHASE 1 & 2")
    logger.info("=" * 60)
    
    # Setup
    if not await setup():
        logger.error("Setup failed. Exiting.")
        return
    
    # Run initial scan
    await run_single_scan()
    
    logger.info("\n✨ Phase 1 & 2 Complete!")
    logger.info("The system can now:")
    logger.info("  1. ✅ Fetch simulated odds from multiple bookmakers")
    logger.info("  2. ✅ Store odds in PostgreSQL database")
    logger.info("  3. ✅ Log activities to file")
    logger.info("\nNext step: Add arbitrage detection (Phase 3)")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)