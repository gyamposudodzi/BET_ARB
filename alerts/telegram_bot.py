import asyncio
from typing import Optional, Callable, Any
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config.settings import settings
from loguru import logger

class TelegramAlertBot:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.status_provider: Optional[Callable] = None
    
    def set_status_provider(self, provider: Callable):
        """Set callback to provide system status"""
        self.status_provider = provider
    
    async def initialize(self) -> bool:
        """Initialize Telegram bot with command handling"""
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        if not self.chat_id:
            logger.warning("Telegram chat ID not configured")
            return False
        
        try:
            # Create application instance
            self.application = Application.builder().token(self.bot_token).build()
            self.bot = self.application.bot  # Keep reference for sending alerts
            
            # Add command handlers
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            
            # Start bot in background
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Test connection
            me = await self.application.bot.get_me()
            logger.info(f"Telegram bot connected: @{me.username}")
            
            logger.info("✅ Telegram bot initialized (interactive mode)")
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
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.status_provider:
            await update.message.reply_text("⚠️ Status provider not configured.")
            return
            
        try:
            stats = await self.status_provider()
            
            msg = (
                f"🤖 <b>Arbitrage Bot Status</b>\n\n"
                f"🟢 <b>State:</b> {'Running' if stats.get('running') else 'Stopped'}\n"
                f"🔄 <b>Scans:</b> {stats.get('scans', 0)}\n"
                f"🎯 <b>Opportunities:</b> {stats.get('opportunities', 0)}\n\n"
                f"📊 <b>Database Stats</b>\n"
                f"• Sports: {stats.get('db_stats', {}).get('active_sports', 0)}\n"
                f"• Bookmakers: {stats.get('db_stats', {}).get('active_bookmakers', 0)}\n"
                f"• Opps Today: {stats.get('db_stats', {}).get('opportunities_today', 0)}\n"
            )
            
            await update.message.reply_text(msg, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error handling status command: {e}")
            await update.message.reply_text("❌ Error retrieving status.")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        msg = (
            "🤖 <b>Bot Commands</b>\n\n"
            "/status - Check bot health and stats\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

    async def close(self):
        """Close bot connection properly"""
        try:
            if self.application:
                # Stop updater if running (prevents "Updater is still running" error)
                if self.application.updater and self.application.updater.running:
                    await self.application.updater.stop()
                
                # Stop application
                await self.application.stop()
                await self.application.shutdown()
            
            logger.info("✅ Telegram bot closed properly")
        except Exception as e:
            logger.error(f"Error closing Telegram bot: {e}")