========
Usage
========

To use django-telegrambot in a app, create a telegrambot.py module in your app as follow::

    # Example code for telegrambot.py module
    from telegram.ext import CommandHandler, MessageHandler, Filters
    from django_telegrambot.apps import DjangoTelegramBot

    import logging
    logger = logging.getLogger(__name__)


    # Define a few command handlers. These usually take the two arguments bot and
    # update. Error handlers also receive the raised TelegramError object in error.
    def start(bot, update):
        bot.sendMessage(update.message.chat_id, text='Hi!')


    def help(bot, update):
        bot.sendMessage(update.message.chat_id, text='Help!')


    def echo(bot, update):
        bot.sendMessage(update.message.chat_id, text=update.message.text)


    def error(bot, update, error):
        logger.warning('Update "%s" caused error "%s"' % (update, error))


    def main():
        logger.info("Loading handlers for telegram bot")

        # Default dispatcher (this is related to the first bot in settings.DJANGO_TELEGRAMBOT['BOTS'])
        app = DjangoTelegramBot.application
        # To get Application related to a specific bot
        # app = DjangoTelegramBot.get_application('BOT_n_token')     #get by bot token
        # app = DjangoTelegramBot.get_application('BOT_n_username')  #get by bot username

        # on different commands - answer in Telegram
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help))

        # on noncommand i.e message - echo the message on Telegram
        app.add_handler(MessageHandler([Filters.text], echo))

        # log all errors
        app.add_error_handler(error)
