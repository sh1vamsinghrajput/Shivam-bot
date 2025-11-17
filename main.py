#!/usr/bin/env python3
"""
Shivam AI Telegram Bot for Pella Hosting
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot_handlers import BotHandlers
from config import BOT_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """Start Telegram bot for Pella"""
    logger.info("🚀 Starting Shivam AI Bot on Pella...")
    
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Initialize handlers
        handlers = BotHandlers()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("menu", handlers.menu_command))
        application.add_handler(CommandHandler("clear", handlers.clear_command))
        application.add_handler(CommandHandler("broadcast", handlers.broadcast_command))
        application.add_handler(CommandHandler("help", handlers.help_command))
        
        # Add callback query handler for buttons
        application.add_handler(CallbackQueryHandler(handlers.button_callback))
        
        # Add message handler for regular messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
        
        logger.info("✅ Bot handlers configured successfully")
        logger.info("🔄 Starting bot polling...")
        
        # Start the bot
        application.run_polling(allowed_updates=["message", "callback_query"])
        
    except Exception as e:
        logger.error(f"❌ Critical error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()