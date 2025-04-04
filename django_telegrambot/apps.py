# coding=utf-8
# django_telegram_bot/apps.py
import os.path
import importlib
import logging
from time import sleep
import asyncio
from asgiref.sync import async_to_sync
from django.apps import AppConfig
from django.apps import apps
from django.conf import settings
from django.utils.module_loading import module_has_submodule

from telegram.ext import Application
from telegram.ext import ApplicationBuilder
from telegram.error import InvalidToken, RetryAfter, TelegramError


logger = logging.getLogger(__name__)


TELEGRAM_BOT_MODULE_NAME = settings.DJANGO_TELEGRAMBOT.get('BOT_MODULE_NAME', 'telegrambot')
WEBHOOK_MODE, POLLING_MODE = range(2)


class classproperty(property):
    def __get__(self, obj, objtype=None):
        return super(classproperty, self).__get__(objtype)
    def __set__(self, obj, value):
        super(classproperty, self).__set__(type(obj), value)
    def __delete__(self, obj):
        super(classproperty, self).__delete__(type(obj))


class DjangoTelegramBot(AppConfig):

    name = 'django_telegrambot'
    verbose_name = 'Django TelegramBot'
    ready_run = False
    bot_tokens = []
    bot_usernames = []
    bot_applications = []
    __used_tokens = set()

    @classproperty
    def application(cls):
        #print("Getting value default dispatcher")
        cls.__used_tokens.add(cls.bot_tokens[0])
        return cls.bot_applications[0]

    @classproperty
    def updater(cls):
        #print("Getting value default updater")
        cls.__used_tokens.add(cls.bot_tokens[0])
        return cls.bot_applications[0].updater

    @classmethod
    def get_application(cls, bot_id=None, safe=True):
        if bot_id is None:
            cls.__used_tokens.add(cls.bot_tokens[0])
            return cls.bot_applications[0]
        else:
            try:
                index = cls.bot_tokens.index(bot_id)
            except ValueError:
                if not safe:
                    return None
                try:
                    index = cls.bot_usernames.index(bot_id)
                except ValueError:
                    return None
            cls.__used_tokens.add(cls.bot_tokens[index])
            return cls.bot_applications[index]

    @classmethod
    def get_bot(cls, bot_id=None, safe=True):
        if bot_id is None:
            if safe:
                return cls.bot_applications[0].bot
            else:
                return None
        else:
            try:
                index = cls.bot_tokens.index(bot_id)
            except ValueError:
                if not safe:
                    return None
                try:
                    index = cls.bot_usernames.index(bot_id)
                except ValueError:
                    return None
            return cls.bot_applications[index].bot

    @classmethod
    def get_updater(cls, bot_id=None, safe=True):
        if bot_id is None:
            return cls.bot_applications[0].updater
        else:
            try:
                index = cls.bot_tokens.index(bot_id)
            except ValueError:
                if not safe:
                    return None
                try:
                    index = cls.bot_usernames.index(bot_id)
                except ValueError:
                    return None
            return cls.bot_applications[index].updater

    def ready(self):
        if DjangoTelegramBot.ready_run:
            return
        DjangoTelegramBot.ready_run = True

        self.mode = WEBHOOK_MODE
        if settings.DJANGO_TELEGRAMBOT.get('MODE', 'WEBHOOK') == 'POLLING':
            self.mode = POLLING_MODE

        modes = ['WEBHOOK','POLLING']
        logger.info('Django Telegram Bot <{} mode>'.format(modes[self.mode]))

        bots_list = settings.DJANGO_TELEGRAMBOT.get('BOTS', [])

        if self.mode == WEBHOOK_MODE:
            webhook_site = settings.DJANGO_TELEGRAMBOT.get('WEBHOOK_SITE', None)
            if not webhook_site:
                logger.warning('Required TELEGRAM_WEBHOOK_SITE missing in settings')
                return
            if webhook_site.endswith("/"):
                webhook_site = webhook_site[:-1]

            webhook_base = settings.DJANGO_TELEGRAMBOT.get('WEBHOOK_PREFIX','/')
            if webhook_base.startswith("/"):
                webhook_base = webhook_base[1:]
            if webhook_base.endswith("/"):
                webhook_base = webhook_base[:-1]

            cert = settings.DJANGO_TELEGRAMBOT.get('WEBHOOK_CERTIFICATE', None)
            certificate = None
            if cert and os.path.exists(cert):
                logger.info('WEBHOOK_CERTIFICATE found in {}'.format(cert))
                certificate=open(cert, 'rb')
            elif cert:
                logger.error('WEBHOOK_CERTIFICATE not found in {} '.format(cert))

        for b in bots_list:
            token = b.get('TOKEN', None)
            context = b.get('CONTEXT', False)
            if not token:
                continue

            allowed_updates = b.get('ALLOWED_UPDATES', None)
            timeout = b.get('TIMEOUT', None)
            proxy = b.get('PROXY', None)

            builder = ApplicationBuilder().token(token)
            if context:
                builder = builder.context_types(context)
            if proxy:
                builder = builder.proxy(proxy['proxy_url'])
            application:Application = builder.build()
            asyncio.run(application.initialize())
            bot = application.bot
            DjangoTelegramBot.bot_applications.append(application)
            if self.mode == WEBHOOK_MODE:
                try:
                    hook_url = '{}/{}/{}/'.format(webhook_site, webhook_base, token)
                    max_connections = b.get('WEBHOOK_MAX_CONNECTIONS', 40)
                    setted = bot.setWebhook(hook_url, certificate=certificate, timeout=timeout, max_connections=max_connections, allowed_updates=allowed_updates)
                    webhook_info = bot.getWebhookInfo()
                    real_allowed = webhook_info.allowed_updates if webhook_info.allowed_updates else ["ALL"]
                    logger.info('Telegram Bot <{}> setting webhook [ {} ] max connections:{} allowed updates:{} pending updates:{} : {}'.format(bot.username, webhook_info.url, webhook_info.max_connections, real_allowed, webhook_info.pending_update_count, setted))
                except InvalidToken:
                    logger.error('Invalid Token : {}'.format(token))
                    return
                except RetryAfter as er:
                    logger.debug('Error: "{}". Will retry in {} seconds'.format(
                            er.message,
                            er.retry_after
                        )
                    )
                    sleep(er.retry_after)
                    self.ready()
                except TelegramError as er:
                    logger.error('Error: "{}"'.format(er.message))
                    return

            else:
                try:
                    asyncio.run(bot.delete_webhook())
                except RetryAfter as er:
                    logger.debug('Error: "{}". Will retry in {} seconds'.format(
                            er.message,
                            er.retry_after
                        )
                    )
                    sleep(er.retry_after)
                    self.ready()
                except TelegramError as er:
                    logger.error('Error: "{}"'.format(er.message))
                    return

            DjangoTelegramBot.bot_tokens.append(token)
            DjangoTelegramBot.bot_usernames.append(bot.username)


        logger.debug('Telegram Bot <{}> set as default bot'.format(DjangoTelegramBot.bot_usernames[0]))

        def module_imported(module_name, method_name, execute):
            try:
                m = importlib.import_module(module_name)
                if execute and hasattr(m, method_name):
                    logger.debug('Run {}.{}()'.format(module_name,method_name))
                    getattr(m, method_name)()
                else:
                    logger.debug('Run {}'.format(module_name))

            except ImportError as er:
                if settings.DJANGO_TELEGRAMBOT.get('STRICT_INIT'):
                    raise er
                else:
                    logger.error('{} : {}'.format(module_name, repr(er)))
                    return False

            return True

        # import telegram bot handlers for all INSTALLED_APPS
        for app_config in apps.get_app_configs():
            if module_has_submodule(app_config.module, TELEGRAM_BOT_MODULE_NAME):
                module_name = '%s.%s' % (app_config.name, TELEGRAM_BOT_MODULE_NAME)
                if module_imported(module_name, 'main', True):
                    logger.info('Loaded {}'.format(module_name))

        num_bots=len(DjangoTelegramBot.__used_tokens)
        if self.mode == POLLING_MODE and num_bots>0:
            logger.info('Please manually start polling update for {0} bot{1}. Run command{1}:'.format(num_bots, 's' if num_bots>1 else ''))
            for token in DjangoTelegramBot.__used_tokens:
                updater = DjangoTelegramBot.get_updater(bot_id=token)
                logger.info('python manage.py botpolling --username={}'.format(updater.bot.username))
