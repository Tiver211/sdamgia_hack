from telegram_bot.bot import bot, init_system, logger

if __name__ == '__main__':
    init_system()
    logger.info('Polling started')
    bot.infinity_polling(timeout=10, long_polling_timeout = 5)
