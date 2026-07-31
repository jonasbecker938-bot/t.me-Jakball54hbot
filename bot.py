import logging
import os
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import json
import random
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store active polls and quizzes (in production, use a database)
user_sessions = {}

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when /start is issued."""
    welcome_text = """
🌟 **Welcome to Poll & Quiz Creator Bot!** 🌟

I can help you create interactive polls and quizzes for your group or channel.

**Commands:**
/poll - Create a new poll
/quiz - Create a new quiz
/help - Show this help message
/cancel - Cancel current operation

**How to use:**
1. Click /poll or /quiz
2. Follow the prompts to create your question
3. Share the poll/quiz with your group!

Made with ❤️ for Telegram
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    help_text = """
📖 **Help & Commands**

/poll - Create a poll with multiple options
/quiz - Create a quiz with a correct answer
/cancel - Cancel current operation

**Poll Features:**
- Anonymous or public voting
- Multiple answers allowed
- Real-time results

**Quiz Features:**
- Single correct answer
- Explanation option
- Score tracking

Need more help? Contact @YourSupportHandle
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel the current operation."""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("✅ Operation cancelled. Start again with /poll or /quiz")
    else:
        await update.message.reply_text("ℹ️ No active operation to cancel")

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start poll creation process."""
    user_id = update.effective_user.id
    user_sessions[user_id] = {'type': 'poll', 'step': 'question'}
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 **Create a Poll**\n\n"
        "Send me the question for your poll.\n"
        "Example: \"What's your favorite programming language?\"",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start quiz creation process."""
    user_id = update.effective_user.id
    user_sessions[user_id] = {'type': 'quiz', 'step': 'question'}
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 **Create a Quiz**\n\n"
        "Send me the question for your quiz.\n"
        "Example: \"What is the capital of France?\"",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages during poll/quiz creation."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_sessions:
        await update.message.reply_text(
            "Start by using /poll or /quiz commands!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Create Poll", callback_data='create_poll')],
                [InlineKeyboardButton("🧠 Create Quiz", callback_data='create_quiz')]
            ])
        )
        return
    
    session = user_sessions[user_id]
    
    if session['step'] == 'question':
        session['question'] = text
        session['step'] = 'options'
        session['options'] = []
        await update.message.reply_text(
            "📝 Great! Now send me the options for your poll/quiz.\n"
            "Send one option per message.\n"
            "When you're done, type **/done** or press '✅ Done'.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done", callback_data='done_options')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )
    
    elif session['step'] == 'options':
        if text == '/done':
            if len(session['options']) < 2:
                await update.message.reply_text(
                    "⚠️ You need at least 2 options! Please add more options or /cancel"
                )
                return
            
            if session['type'] == 'poll':
                await create_poll(update, context, session)
            else:
                await create_quiz_question(update, context, session)
            return
        
        session['options'].append(text)
        option_num = len(session['options'])
        await update.message.reply_text(
            f"✅ Option {option_num} added: \"{text}\"\n"
            f"Add more options or type **/done** to finish.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done", callback_data='done_options')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )

async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict) -> None:
    """Create and send the poll."""
    options = session['options']
    
    keyboard = [
        [InlineKeyboardButton("📊 View Results", callback_data=f"poll_results_{update.effective_user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_poll(
        question=session['question'],
        options=options,
        is_anonymous=True,
        allows_multiple_answers=True,
        explanation="Vote now!",
        reply_markup=reply_markup
    )
    
    await update.message.reply_text("✅ Poll created successfully!")
    del user_sessions[update.effective_user.id]

async def create_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict) -> None:
    """Create and send the quiz."""
    options = session['options']
    
    # Ask which option is correct
    option_buttons = []
    for i, option in enumerate(options):
        option_buttons.append([
            InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"quiz_correct_{i}")
        ])
    option_buttons.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    
    reply_markup = InlineKeyboardMarkup(option_buttons)
    
    await update.message.reply_text(
        f"🧠 **Quiz Question:** {session['question']}\n\n"
        f"Select the correct answer:\n",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    session['step'] = 'correct_answer'

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'cancel':
        if user_id in user_sessions:
            del user_sessions[user_id]
        await query.edit_message_text("✅ Operation cancelled. Start again with /poll or /quiz")
        return
    
    if data == 'done_options':
        if user_id not in user_sessions:
            await query.edit_message_text("Please start with /poll or /quiz first")
            return
        
        session = user_sessions[user_id]
        if len(session['options']) < 2:
            await query.edit_message_text(
                "⚠️ You need at least 2 options! Please add more options or /cancel"
            )
            return
        
        if session['type'] == 'poll':
            await create_poll(update, context, session)
        else:
            await create_quiz_question(update, context, session)
        return
    
    if data.startswith('quiz_correct_'):
        if user_id not in user_sessions:
            await query.edit_message_text("Session expired. Start again with /quiz")
            return
        
        correct_index = int(data.split('_')[2])
        session = user_sessions[user_id]
        
        # Create the quiz
        await update.effective_message.reply_poll(
            question=session['question'],
            options=session['options'],
            type=Poll.QUIZ,
            correct_option_id=correct_index,
            explanation="Here's the correct answer! 🎯",
            explanation_parse_mode="Markdown"
        )
        
        await query.edit_message_text("✅ Quiz created successfully!")
        if user_id in user_sessions:
            del user_sessions[user_id]
        return
    
    if data.startswith('poll_results_'):
        # Simple placeholder for results
        await query.edit_message_text(
            "📊 Poll results are being compiled...\n"
            "Check back later for detailed statistics!"
        )
        return
    
    if data.startswith('create_'):
        await query.edit_message_text("Please use the /poll or /quiz commands to get started.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text(
        "❌ Unknown command. Use /start to see available commands."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify user."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again or use /start"
        )

# --- Main Function ---

def main() -> None:
    """Start the bot."""
    # Get token from environment variable
    token = os.environ.get('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("poll", poll))
    application.add_handler(CommandHandler("quiz", quiz))
    
    # Add handlers for text and callbacks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add unknown command handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
