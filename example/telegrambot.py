# -*- coding: utf-8 -*-
# Example code for telegrambot.py module
from telegram.ext import CommandHandler, MessageHandler, filters
from django_telegrambot.apps import DjangoTelegramBot

import logging
logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    context.bot.sendMessage(update.message.chat_id, text='Hi!')


def help(update, context):
    context.bot.sendMessage(update.message.chat_id, text='Help!')


def echo(update, context):
    context.bot.sendMessage(update.message.chat_id, text=update.message.text)


def error(update, context, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    logger.info("Loading handlers for telegram bot")

    # Default dispatcher (this is related to the first bot in settings.TELEGRAM_BOT_TOKENS)
    app = DjangoTelegramBot.application
    # To get Dispatcher related to a specific bot
    # app = DjangoTelegramBot.getDispatcher('BOT_n_token')     #get by bot token
    # app = DjangoTelegramBot.getDispatcher('BOT_n_username')  #get by bot username

    # on different commands - answer in Telegram
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    app.add_handler(MessageHandler([filters.TEXT], echo))

    # log all errors
    app.add_error_handler(error)

    # log all errors
    app.addErrorHandler(error)

