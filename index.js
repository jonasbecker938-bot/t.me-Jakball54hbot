const TelegramBot = require('node-telegram-bot-api');

const token = process.env.BOT_TOKEN;
if (!token) {
    console.error('❌ BOT_TOKEN is not set!');
    process.exit(1);
}

console.log('🤖 Starting Poll & Quiz Bot...');

const bot = new TelegramBot(token, { polling: true });
const userSessions = {};

// Error handlers
bot.on('error', (error) => console.error('Bot error:', error));
bot.on('polling_error', (error) => console.error('Polling error:', error));

// Commands
bot.onText(/\/start/, (msg) => {
    bot.sendMessage(msg.chat.id, 
        `🌟 Welcome to Poll & Quiz Creator Bot! 🌟

Commands:
/poll - Create a new poll
/quiz - Create a new quiz
/help - Show help
/cancel - Cancel operation`
    );
});

bot.onText(/\/help/, (msg) => {
    bot.sendMessage(msg.chat.id,
        `📖 Commands
/poll - Create a poll
/quiz - Create a quiz
/cancel - Cancel current operation`
    );
});

bot.onText(/\/cancel/, (msg) => {
    const userId = msg.from.id;
    if (userSessions[userId]) {
        delete userSessions[userId];
        bot.sendMessage(msg.chat.id, '✅ Cancelled!');
    } else {
        bot.sendMessage(msg.chat.id, 'ℹ️ Nothing to cancel');
    }
});

bot.onText(/\/poll/, (msg) => {
    const userId = msg.from.id;
    userSessions[userId] = { type: 'poll', step: 'question' };
    bot.sendMessage(msg.chat.id, '📝 Send me the poll question:', {
        reply_markup: {
            inline_keyboard: [[{ text: '❌ Cancel', callback_data: 'cancel' }]]
        }
    });
});

bot.onText(/\/quiz/, (msg) => {
    const userId = msg.from.id;
    userSessions[userId] = { type: 'quiz', step: 'question' };
    bot.sendMessage(msg.chat.id, '📝 Send me the quiz question:', {
        reply_markup: {
            inline_keyboard: [[{ text: '❌ Cancel', callback_data: 'cancel' }]]
        }
    });
});

// Handle messages
bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const text = msg.text;
    
    if (!text || text.startsWith('/')) return;
    if (!userSessions[userId]) {
        bot.sendMessage(chatId, 'Use /poll or /quiz first!');
        return;
    }
    
    const session = userSessions[userId];
    
    if (session.step === 'question') {
        session.question = text;
        session.step = 'options';
        session.options = [];
        bot.sendMessage(chatId, '📝 Send options (one per message). Type /done when finished.', {
            reply_markup: {
                inline_keyboard: [
                    [{ text: '✅ Done', callback_data: 'done_options' }],
                    [{ text: '❌ Cancel', callback_data: 'cancel' }]
                ]
            }
        });
    } else if (session.step === 'options') {
        if (text === '/done') {
            if (session.options.length < 2) {
                bot.sendMessage(chatId, '⚠️ Need at least 2 options!');
                return;
            }
            if (session.type === 'poll') {
                createPoll(chatId, session);
            } else {
                createQuizQuestion(chatId, session);
            }
            return;
        }
        session.options.push(text);
        bot.sendMessage(chatId, `✅ Option ${session.options.length} added!`);
    }
});

// Handle callbacks
bot.on('callback_query', (callbackQuery) => {
    const chatId = callbackQuery.message.chat.id;
    const userId = callbackQuery.from.id;
    const data = callbackQuery.data;
    const messageId = callbackQuery.message.message_id;
    
    bot.answerCallbackQuery(callbackQuery.id);
    
    if (data === 'cancel') {
        if (userSessions[userId]) delete userSessions[userId];
        bot.editMessageText('✅ Cancelled!', { chat_id: chatId, message_id: messageId });
        return;
    }
    
    if (data === 'done_options') {
        if (!userSessions[userId]) {
            bot.editMessageText('Start with /poll or /quiz', { chat_id: chatId, message_id: messageId });
            return;
        }
        const session = userSessions[userId];
        if (session.options.length < 2) {
            bot.editMessageText('⚠️ Need at least 2 options!', { chat_id: chatId, message_id: messageId });
            return;
        }
        if (session.type === 'poll') {
            createPollFromCallback(chatId, messageId, session);
        } else {
            createQuizFromCallback(chatId, messageId, session);
        }
        return;
    }
    
    if (data.startsWith('correct_')) {
        if (!userSessions[userId]) {
            bot.editMessageText('Session expired. Use /quiz', { chat_id: chatId, message_id: messageId });
            return;
        }
        const correctIndex = parseInt(data.split('_')[1]);
        const session = userSessions[userId];
        bot.sendPoll(chatId, session.question, session.options, {
            type: 'quiz',
            correct_option_id: correctIndex,
            explanation: 'Correct answer! 🎯'
        });
        bot.editMessageText('✅ Quiz created!', { chat_id: chatId, message_id: messageId });
        delete userSessions[userId];
    }
});

function createPoll(chatId, session) {
    bot.sendPoll(chatId, session.question, session.options, {
        is_anonymous: true,
        allows_multiple_answers: true
    });
    bot.sendMessage(chatId, '✅ Poll created!');
    delete userSessions[chatId];
}

function createQuizQuestion(chatId, session) {
    const options = session.options;
    const inlineKeyboard = options.map((option, index) => {
        return [{ text: `${index+1}. ${option}`, callback_data: `correct_${index}` }];
    });
    inlineKeyboard.push([{ text: '❌ Cancel', callback_data: 'cancel' }]);
    bot.sendMessage(chatId, '🧠 Select the correct answer:', {
        reply_markup: { inline_keyboard: inlineKeyboard }
    });
    session.step = 'correct_answer';
}

function createPollFromCallback(chatId, messageId, session) {
    bot.sendPoll(chatId, session.question, session.options, {
        is_anonymous: true,
        allows_multiple_answers: true
    });
    bot.editMessageText('✅ Poll created!', { chat_id: chatId, message_id: messageId });
    delete userSessions[chatId];
}

function createQuizFromCallback(chatId, messageId, session) {
    const options = session.options;
    const inlineKeyboard = options.map((option, index) => {
        return [{ text: `${index+1}. ${option}`, callback_data: `correct_${index}` }];
    });
    inlineKeyboard.push([{ text: '❌ Cancel', callback_data: 'cancel' }]);
    bot.editMessageText('🧠 Select the correct answer:', {
        chat_id: chatId,
        message_id: messageId,
        reply_markup: { inline_keyboard: inlineKeyboard }
    });
    session.step = 'correct_answer';
}

console.log('✅ Bot is running successfully!');
