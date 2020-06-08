import logging
import sys
from utils import ts
from logging.handlers import TimedRotatingFileHandler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(f"%(asctime)s — %(levelname)s — %(message)s")
    logger.addHandler(get_console_handler(formatter))
    # logger.addHandler(get_file_handler(name, formatter))
    logger.propagate = False
    return logger


def get_console_handler(formatter):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler


def get_file_handler(name, formatter):
    handler = TimedRotatingFileHandler(f"../{name}-{ts.from_utcnow_to_string('%Y%m%d')}.log", when='midnight')
    handler.setFormatter(formatter)
    return handler
