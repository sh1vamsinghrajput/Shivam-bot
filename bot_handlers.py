import logging
import asyncio
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import BotDatabase
from venice_ai import VeniceAI
from config import WELCOME_MESSAGE, DEVELOPER_USERNAME, ADMIN_CHAT_ID

class BotHandlers:
    def __init__(self):
        self.db = BotDatabase()
        self.ai = VeniceAI()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Add user to database
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Mark user as verified (no verification needed)
        self.db.verify_user(user.id)
        
        await self.send_welcome_message(update, context)
    
    async def send_welcome_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        keyboard = [
            [InlineKeyboardButton("🤖 Chat with AI", callback_data="chat_worm")],
            [InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER_USERNAME.replace('@', '')}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            WELCOME_MESSAGE,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup
        )
    
    async def send_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send main menu to users"""
        keyboard = [
            [InlineKeyboardButton("🤖 Chat with AI", callback_data="chat_worm")],
            [InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER_USERNAME.replace('@', '')}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"🎯 **Shivam AI Assistant**\n\nHello {update.effective_user.first_name}! How can I assist you today?"
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "chat_worm":
            await query.edit_message_text(
                "🤖 **AI Chat Mode Activated**\n\nYou can now ask me anything! Just type your question and I'll respond with AI-powered answers.\n\n💡 *Type /menu to return to main menu*",
                parse_mode=ParseMode.MARKDOWN
            )
            # Set user state to chat mode
            context.user_data['chat_mode'] = True
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user_id = update.effective_user.id
        
        # Add user to database if not exists and mark as verified
        user = update.effective_user
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        self.db.verify_user(user.id)
        
        # Check if in chat mode
        if not context.user_data.get('chat_mode', False):
            await self.send_main_menu(update, context)
            return
        
        # Process AI chat
        await self.handle_ai_chat(update, context)
    
    async def handle_ai_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI chat interaction with enhanced memory and concurrent processing"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get enhanced conversation context (includes memory)
            context_data = self.db.get_enhanced_conversation_context(user_id)
            conversation_history = context_data["conversation_history"]
            context_memory = context_data["context_memory"]
            
            # Detect and store context information from user message (async)
            await self.analyze_and_store_context(user_id, user_message)
            
            # Prepare enhanced prompt with context memory
            enhanced_history = self.prepare_enhanced_prompt(conversation_history, context_memory, user_message)
            
            # Get AI response with timeout to prevent blocking
            ai_response = await asyncio.wait_for(
                asyncio.to_thread(self.ai.get_ai_response, enhanced_history, user_message),
                timeout=30.0
            )
            
            # Save conversation asynchronously
            await asyncio.gather(
                asyncio.to_thread(self.db.add_conversation, user_id, "user", user_message),
                asyncio.to_thread(self.db.add_conversation, user_id, "assistant", ai_response)
            )
            
            # Send response with improved formatting
            await self.send_improved_response(update, context, ai_response)
            
        except asyncio.TimeoutError:
            await update.message.reply_text("⏰ Request timed out. Please try again.")
        except Exception as e:
            logging.error(f"Error in AI chat: {e}")
            await update.message.reply_text("❌ Something went wrong. Please try again.")
    
    async def analyze_and_store_context(self, user_id: int, message: str):
        """Analyze message and store relevant context information"""
        message_lower = message.lower()
        
        # Detect tool/project creation requests
        if any(keyword in message_lower for keyword in ['make', 'create', 'build', 'tool', 'project', 'app']):
            if 'python' in message_lower:
                self.db.store_context_memory(user_id, "current_project", f"Python project: {message[:100]}")
            elif 'website' in message_lower or 'web' in message_lower:
                self.db.store_context_memory(user_id, "current_project", f"Web project: {message[:100]}")
            else:
                self.db.store_context_memory(user_id, "current_project", f"General project: {message[:100]}")
        
        # Detect improvement/modification requests
        if any(keyword in message_lower for keyword in ['better', 'improve', 'enhance', 'add', 'modify', 'change']):
            self.db.store_context_memory(user_id, "last_request", f"Improvement request: {message[:100]}")
        
        # Store user preferences
        if 'like' in message_lower or 'want' in message_lower or 'prefer' in message_lower:
            self.db.store_context_memory(user_id, "user_preferences", message[:150])
    
    def prepare_enhanced_prompt(self, conversation_history: List[dict], context_memory: List[dict], current_message: str) -> List[dict]:
        """Prepare enhanced prompt with context memory for better continuity"""
        enhanced_history = []
        
        # Add context memory as system context
        if context_memory:
            context_summary = []
            for ctx in context_memory:
                if ctx["type"] == "current_project":
                    context_summary.append(f"Current project context: {ctx['data']}")
                elif ctx["type"] == "last_request":
                    context_summary.append(f"Previous request: {ctx['data']}")
                elif ctx["type"] == "user_preferences":
                    context_summary.append(f"User preference: {ctx['data']}")
            
            if context_summary:
                system_context = {
                    "role": "system",
                    "content": f"Context from previous conversations: {' | '.join(context_summary[:3])}"
                }
                enhanced_history.append(system_context)
        
        # Add conversation history
        enhanced_history.extend(conversation_history)
        
        return enhanced_history
    
    async def send_improved_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, full_response: str):
        """Send response with improved code formatting and no rate limiting issues"""
        try:
            # Clean and format the response
            clean_response = self.format_ai_response_improved(full_response)
            
            # Send direct response without streaming to avoid rate limits
            final_text = f"🤖 {clean_response}"
            
            # Use HTML parsing for better code formatting
            if "```" in clean_response or "<pre>" in clean_response:
                await update.message.reply_text(final_text, parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(final_text)
                
        except Exception as e:
            logging.error(f"Error in improved response: {e}")
            # Fallback to simple text
            await update.message.reply_text(f"🤖 {full_response}")
    
    def format_ai_response_improved(self, response: str) -> str:
        """Improved AI response formatting with better code block handling"""
        import re
        
        # Convert markdown code blocks to HTML for Telegram
        def replace_code_blocks(text):
            # Pattern to match code blocks with optional language
            pattern = r'```(\w*)\n?(.*?)```'
            def code_replacement(match):
                language = match.group(1) if match.group(1) else ''
                code_content = match.group(2).strip()
                
                # Format for Telegram HTML
                return f'<pre><code class="{language}">{code_content}</code></pre>'
            
            return re.sub(pattern, code_replacement, text, flags=re.DOTALL)
        
        def replace_inline_code(text):
            # Replace inline code with HTML
            return re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Apply formatting
        formatted_response = replace_code_blocks(response)
        formatted_response = replace_inline_code(formatted_response)
        
        # Clean up extra whitespace
        formatted_response = re.sub(r'\n{3,}', '\n\n', formatted_response)
        
        return formatted_response.strip()
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command"""
        user_id = update.effective_user.id
        
        # Add user to database if not exists and mark as verified
        user = update.effective_user
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        self.db.verify_user(user.id)
        
        # Disable chat mode
        context.user_data['chat_mode'] = False
        await self.send_main_menu(update, context)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command to clear conversation history"""
        user_id = update.effective_user.id
        
        # Add user to database if not exists and mark as verified
        user = update.effective_user
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        self.db.verify_user(user.id)
        
        self.db.clear_conversation(user_id)
        await update.message.reply_text("🗑️ **Conversation cleared!**\n\nYour chat history has been reset.", parse_mode=ParseMode.MARKDOWN)
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command (admin only)"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        # Get message to broadcast
        if not context.args:
            await update.message.reply_text(
                "📢 **Broadcast Usage:**\n\n`/broadcast Your message here`\n\nExample:\n`/broadcast Hello everyone! New updates available.`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        broadcast_message = " ".join(context.args)
        users = self.db.get_all_users()
        
        if not users:
            await update.message.reply_text("❌ No users found for broadcasting.")
            return
        
        # Send broadcast
        success_count = 0
        failed_count = 0
        
        progress_message = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
        
        for user_id_target in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id_target,
                    text=f"📢 **Broadcast Message**\n\n{broadcast_message}",
                    parse_mode=ParseMode.MARKDOWN
                )
                success_count += 1
            except Exception as e:
                logging.warning(f"Failed to send broadcast to {user_id_target}: {e}")
                failed_count += 1
        
        await progress_message.edit_text(
            f"✅ **Broadcast Complete!**\n\n📊 **Statistics:**\n• Successfully sent: {success_count}\n• Failed: {failed_count}\n• Total users: {len(users)}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Shivam AI Assistant - Help**

**Available Commands:**
• `/start` - Start the bot
• `/menu` - Return to main menu
• `/clear` - Clear your conversation history
• `/help` - Show this help message

**Features:**
• 🤖 AI-powered conversations
• 👨‍💻 Direct developer contact
• 🔄 Real-time AI responses

**How to use:**
1. Use /start to begin
2. Click "Chat with AI" to start AI conversation
3. Ask any questions - I'll respond with AI assistance!

**Developer:** @PaidModder
"""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)