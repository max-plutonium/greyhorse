import logging.config
import os
import sys

DEBUG_MODE = os.environ.get('DEBUG', False)


LOGGING_CONFIG_DEFAULTS = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        'greyhorse': {
            'level': 'INFO' if not DEBUG_MODE else 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'greyhorse.wtf': {
            'level': 'INFO',
            'handlers': ['error_console'],
            'propagate': True,
            'qualname': 'greyhorse.wtf',
        },
    },
    handlers={
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stdout,
        },
        'error_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stderr,
        },
    },
    formatters={
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter',
        },
        'verbose': {
            'format': '%(asctime)s [%(process)d/%(threadName)s] [%(levelname)-5.8s] '
            '%(message)s (%(name)s:%(module)s:%(lineno)s)',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter',
        },
        'simple': {'format': '%(asctime)s [%(levelname)-5.8s] %(message)s'},
    },
)


logging.config.dictConfig(LOGGING_CONFIG_DEFAULTS)
logger = logging.getLogger('greyhorse')
logger_wtf = logging.getLogger('greyhorse.wtf')
