from telegram_bot.bot import bot, init_system

if __name__ == '__main__':
    init_system()
    bot.infinity_polling(timeout=10, long_polling_timeout = 5)
