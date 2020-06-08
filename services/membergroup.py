from utils import log

LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("memberGroup")