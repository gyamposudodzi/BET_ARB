import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import settings
from loguru import logger

class TelegramAlertBot:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
    
    async def initialize(self):
        """Initialize Telegram bot"""
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            self.bot = Bot(token=self.bot_token)
            self.application = Application.builder().token(self.bot_token).build()
            
            # Register handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("stats", self.stats_command))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            
            # Start polling in background
            asyncio.create_task(self.application.run_polling())
            
            logger.info("✅ Telegram bot initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        message = """
🤖 *Arbitrage Bot is Running!*

*Commands:*
/start - Show this message
/status - Check bot status
/stats - Show statistics
/opportunities - Show recent opportunities

*Features:*
• Real-time arbitrage detection
• Multiple sports and bookmakers
• Automatic alerts for opportunities >0.5%
• SQLite database for tracking

Bot will automatically send alerts when profitable opportunities are found!
        """
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        from database.session import get_db_stats
        
        try:
            stats = await get_db_stats()
            message = f"""
📊 *Bot Status*

*Database Stats:*
• Bookmakers: {stats.get('bookmakers', 0)}
• Sports: {stats.get('sports', 0)}
• Events: {stats.get('events', 0)}
• Odds: {stats.get('odds', 0)}
• Opportunities: {stats.get('opportunities', 0)}
• DB Size: {stats.get('db_size_mb', 0)} MB

*Configuration:*
• Min Profit: {settings.MIN_PROFIT_THRESHOLD}%
• Scan Interval: {settings.SCAN_INTERVAL}s
• Max Stake: ${settings.MAX_STAKE}
            """
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting status: {e}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        from database.crud import get_crud
        
        try:
            async for crud in get_crud():
                stats = await crud.get_stats()
                
                message = f"""
📈 *Today's Statistics*

• Opportunities detected: {stats.get('opportunities_today', 0)}
• Total opportunities: {stats.get('total_opportunities', 0)}
• Average profit: {stats.get('avg_profit_today', 0)}%
• Active bookmakers: {stats.get('active_bookmakers', 0)}
• Active sports: {stats.get('active_sports', 0)}
                """
                
                await update.message.reply_text(message, parse_mode="Markdown")
                break
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting stats: {e}")
    
    async def send_opportunity_alert(self, opportunity):
        """Send arbitrage opportunity alert"""
        if not self.bot or not self.chat_id:
            return
        
        try:
            message = self._format_opportunity_message(opportunity)
            keyboard = self._create_opportunity_keyboard(opportunity)
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            logger.info(f"📨 Sent Telegram alert for {opportunity.profit_percentage}% opportunity")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    async def send_system_alert(self, message: str, level: str = "info"):
        """Send system alert"""
        if not self.bot or not self.chat_id:
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
    
    def _create_opportunity_keyboard(self, opportunity):
        """Create inline keyboard for opportunity actions"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Execute", callback_data=f"execute_{opportunity.id}"),
                InlineKeyboardButton("❌ Ignore", callback_data=f"ignore_{opportunity.id}")
            ],
            [
                InlineKeyboardButton("📊 Details", callback_data=f"details_{opportunity.id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("execute_"):
            await query.edit_message_text(text="⏳ Executing arbitrage opportunity...")
        elif data.startswith("ignore_"):
            await query.edit_message_text(text="❌ Opportunity ignored")
        elif data.startswith("details_"):
            await query.edit_message_text(text="📊 Loading details...")
    
    async def close(self):
        """Close bot connection"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()