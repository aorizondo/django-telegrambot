# coding=utf-8
# django_telegram_bot/apps.py
import importlib
import logging

from django.apps import AppConfig
from django.apps import apps
from django.conf import settings
from django.utils.module_loading import module_has_submodule


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
    bots = []
    updaters = []
    __used_tokens = set()

    @classproperty
    def updater(cls):
        #print("Getting value default updater")
        cls.__used_tokens.add(cls.bot_tokens[0])
        return cls.updaters[0]

    @classmethod
    def get_bot(cls, bot_id=None, safe=True):
        if bot_id is None:
            if safe:
                return cls.bots[0]
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
            return cls.bots[index]


    @classmethod
    def getBot(cls, bot_id=None, safe=True):
        return cls.get_bot(bot_id, safe)


    @classmethod
    def get_updater(cls, bot_id=None, safe=True):
        if bot_id is None:
            return cls.updaters[0]
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
            return cls.updaters[index]


    @classmethod
    def getUpdater(cls, id=None, safe=True):
        return cls.get_updater(id, safe)


    def ready(self):
        if DjangoTelegramBot.ready_run:
            return
        DjangoTelegramBot.ready_run = True
        bots_list = settings.DJANGO_TELEGRAMBOT.get('BOTS', [])
        for b in bots_list:
            token = b.get('TOKEN', None)
            if not token:
                continue
            DjangoTelegramBot.__used_tokens.add(token)
            DjangoTelegramBot.bot_tokens.append(token)
        logger.debug('Telegram Bot <{}> set as default bot'.format(DjangoTelegramBot.bot_tokens[0]))

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
        if num_bots>0:
            logger.info('Please manually start polling update for {0} bot{1}. Run command{1}:'.format(num_bots, 's' if num_bots>1 else ''))
            for token in DjangoTelegramBot.__used_tokens:
                updater = DjangoTelegramBot.get_updater(bot_id=token)
                logger.info('python manage.py botpolling --username={}'.format(updater.bot.username))
