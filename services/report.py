from utils import log

LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("report")


def get_monthly_report():
    # validation

    # query

    # send result to tg group
    pass
