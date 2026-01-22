import asyncio
from typing import Optional
from telegram import Bot
from config.settings import settings
from loguru import logger

class TelegramAlertBot:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot: Optional[Bot] = None
    
    async def initialize(self) -> bool:
        """Initialize Telegram bot (no polling)"""
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        if not self.chat_id:
            logger.warning("Telegram chat ID not configured")
            return False
        
        try:
            # Create bot instance
            self.bot = Bot(token=self.bot_token)
            
            # Test connection
            me = await self.bot.get_me()
            logger.info(f"Telegram bot connected: @{me.username}")
            
            logger.info("✅ Telegram bot initialized (send-only mode)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def send_opportunity_alert(self, opportunity):
        """Send arbitrage opportunity alert"""
        if not self.bot:
            logger.warning("Telegram bot not initialized")
            return
        
        try:
            message = self._format_opportunity_message(opportunity)
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            
            logger.info(f"📨 Sent Telegram alert for {opportunity.profit_percentage}% opportunity")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    async def send_system_alert(self, message: str, level: str = "info"):
        """Send system alert"""
        if not self.bot:
            logger.warning("Telegram bot not initialized")
            return
        
        emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        
        emoji = emojis.get(level, "ℹ️")
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"{emoji} {message}"
            )
        except Exception as e:
            logger.error(f"Failed to send system alert: {e}")
    
    def _format_opportunity_message(self, opportunity) -> str:
        """Format opportunity as HTML message"""
        # Extract outcomes info
        outcomes_text = ""
        for outcome in opportunity.outcomes:
            outcomes_text += f"• {outcome['bookmaker']}: {outcome['outcome']} @ {outcome['odds']}\n"
        
        # Format stakes
        stakes_text = ""
        for key, stake in opportunity.stake_allocations.items():
            bookmaker, outcome = key.split("_")
            stakes_text += f"• {bookmaker} ({outcome}): ${stake}\n"
        
        return f"""
🎯 <b>ARBITRAGE OPPORTUNITY DETECTED!</b>

📊 <b>Profit:</b> <code>{opportunity.profit_percentage}%</code>
⚽ <b>Sport:</b> {opportunity.sport_key}
🎮 <b>Market:</b> {opportunity.market_type}

<b>Odds:</b>
{outcomes_text}

<b>Optimal Stakes (${opportunity.total_investment} total):</b>
{stakes_text}

💰 <b>Guaranteed Return:</b> ${opportunity.guaranteed_return}
🕒 <i>Opportunity expires in {settings.OPPORTUNITY_TIMEOUT} seconds</i>
        """
    
    async def close(self):
        """Close bot connection properly"""
        try:
            if self.bot:
                await self.bot.close()
                logger.info("✅ Telegram bot closed properly")
        except Exception as e:
            logger.error(f"Error closing Telegram bot: {e}")