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


def init():
    global LOGGER
    LOGGER = log.get_logger("main")
    env = config.init()

    neo4j.init()
    settingdao.init()
    memberdao.init()
    membergroupdao.init()
    eventdao.init()

    tg.init(env)
    cache.init()
    event.init()
    security.init()
    member.init()
    membergroup.init()


def cron():
    schedule.every().day.at("04:00").do(tg.monthly_stats)
    schedule.every().day.at("04:01").do(tg.daily_msg)

    while 1:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    init()

    LOGGER.info(f"started, GIT_TAG={os.environ['GIT_TAG'] if 'GIT_TAG' in os.environ else ''}")
    LOGGER.info(f"target neo4j host: {config.get_string('neo4j', 'host')}")

    t = threading.Thread(target=cron)
    t.start()
    LOGGER.info("tg idling")
    tg.get_updates()
    config.reset()



