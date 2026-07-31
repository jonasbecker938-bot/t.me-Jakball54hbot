import logging
import os
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user sessions
user_sessions = {}

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = """
🌟 **Welcome to Poll & Quiz Creator Bot!** 🌟

**Commands:**
/poll - Create a new poll
/quiz - Create a new quiz
/help - Show help
/cancel - Cancel operation
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📖 **Commands**
/poll - Create a poll
/quiz - Create a quiz
/cancel - Cancel current operation
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("✅ Cancelled!")
    else:
        await update.message.reply_text("ℹ️ Nothing to cancel")

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_sessions[user_id] = {'type': 'poll', 'step': 'question'}
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 Send me the poll question:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_sessions[user_id] = {'type': 'quiz', 'step': 'question'}
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 Send me the quiz question:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_sessions:
        await update.message.reply_text("Use /poll or /quiz first!")
        return
    
    session = user_sessions[user_id]
    
    if session['step'] == 'question':
        session['question'] = text
        session['step'] = 'options'
        session['options'] = []
        await update.message.reply_text(
            "📝 Send me options (one per message).\nType /done when finished.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done", callback_data='done_options')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ])
        )
    
    elif session['step'] == 'options':
        if text == '/done':
            if len(session['options']) < 2:
                await update.message.reply_text("⚠️ Need at least 2 options!")
                return
            
            if session['type'] == 'poll':
                await create_poll(update, context, session)
            else:
                await create_quiz_question(update, context, session)
            return
        
        session['options'].append(text)
        await update.message.reply_text(f"✅ Option {len(session['options'])} added!")

async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict) -> None:
    await update.message.reply_poll(
        question=session['question'],
        options=session['options'],
        is_anonymous=True,
        allows_multiple_answers=True,
    )
    await update.message.reply_text("✅ Poll created!")
    del user_sessions[update.effective_user.id]

async def create_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict) -> None:
    options = session['options']
    option_buttons = []
    for i, option in enumerate(options):
        option_buttons.append([
            InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"correct_{i}")
        ])
    option_buttons.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    
    reply_markup = InlineKeyboardMarkup(option_buttons)
    await update.message.reply_text(
        f"🧠 Select the correct answer:",
        reply_markup=reply_markup
    )
    session['step'] = 'correct_answer'

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'cancel':
        if user_id in user_sessions:
            del user_sessions[user_id]
        await query.edit_message_text("✅ Cancelled!")
        return
    
    if data == 'done_options':
        if user_id not in user_sessions:
            await query.edit_message_text("Start with /poll or /quiz")
            return
        
        session = user_sessions[user_id]
        if len(session['options']) < 2:
            await query.edit_message_text("⚠️ Need at least 2 options!")
            return
        
        if session['type'] == 'poll':
            await create_poll_from_callback(update, context, session)
        else:
            await create_quiz_from_callback(update, context, session)
        return
    
    if data.startswith('correct_'):
        if user_id not in user_sessions:
            await query.edit_message_text("Session expired. Use /quiz")
            return
        
        correct_index = int(data.split('_')[1])
        session = user_sessions[user_id]
        
        await update.effective_message.reply_poll(
            question=session['question'],
            options=session['options'],
            type=Poll.QUIZ,
            correct_option_id=correct_index,
            explanation="Correct answer! 🎯"
        )
        
        await query.edit_message_text("✅ Quiz created!")
        del user_sessions[user_id]

async def create_poll_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict) -> None:
    await update.effective_message.reply_poll(
        question=session['question'],
        options=session['options'],
        is_anonymous=True,
        allows_multiple_answers=True,
    )
    await update.callback_query.edit_message_text("✅ Poll created!")
    del user_sessions[update.effective_user.id]

async def create_quiz_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict) -> None:
    options = session['options']
    option_buttons = []
    for i, option in enumerate(options):
        option_buttons.append([
            InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"correct_{i}")
        ])
    option_buttons.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    
    reply_markup = InlineKeyboardMarkup(option_buttons)
    await update.callback_query.edit_message_text(
        f"🧠 Select the correct answer:",
        reply_markup=reply_markup
    )
    session['step'] = 'correct_answer'

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("❌ Unknown command. Use /start")

# --- Main ---

def main() -> None:
    token = os.environ.get('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN not set!")
        return
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("poll", poll))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
