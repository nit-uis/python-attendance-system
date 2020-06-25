import sys
import threading
import schedule
import time
from configs import config
from services import event, member, membergroup, security, cache
from utils import log, tg
from db import neo4j
from dao import membergroupdao, settingdao, memberdao, eventdao
import os

LOGGER = None
ENV = ""


def init():
    global LOGGER, ENV
    LOGGER = log.get_logger("main")
    env = config.init()
    ENV = env[1]

    neo4j.init()
    settingdao.init()
    memberdao.init()
    membergroupdao.init()
    eventdao.init()

    tg.init(env[0])
    cache.init()
    event.init()
    security.init()
    member.init()
    membergroup.init()


def _cron():
    tg.monthly_stats()
    tg.daily_msg()


def cron():
    schedule.every().day.at("04:00").do(_cron)

    while 1:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    init()

    LOGGER.info(f"started, GIT_TAG={os.environ['GIT_TAG'] if 'GIT_TAG' in os.environ else ''}")
    LOGGER.info(f"target neo4j host: {config.get_string('neo4j', 'host')}")

    if "cron" in ENV:
        _cron()
        exit(1)

    t = threading.Thread(target=cron)
    t.start()
    LOGGER.info("tg idling")
    tg.get_updates()
    config.reset()



