import logging
import sys
from utils import ts
from logging.handlers import TimedRotatingFileHandler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(f"%(asctime)s — %(levelname)s — %(message)s")
    logger.addHandler(get_console_handler(formatter))
    logger.propagate = False
    return logger


def get_console_handler(formatter):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler


# def getFileHandler(cineplex, formatter):
#     handler = TimedRotatingFileHandler(f"../{cineplex}-{ts.fromUtcnowToString('%Y%m%d')}-4.log", when='midnight')
#     handler.setFormatter(formatter)
#     return handler
