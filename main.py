import schedule
import time
from configs import config
from services import event, member, membergroup, report
from utils import log, tg, formatter
from db import neo4j
from dao import membergroupdao, settingdao, reportdao, memberdao, eventdao
import os

LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("main")
    env = config.init()

    neo4j.init()
    settingdao.init()
    reportdao.init()
    memberdao.init()
    membergroupdao.init()
    eventdao.init()

    tg.init(env)
    event.init()
    report.init()
    member.init()
    membergroup.init()


if __name__ == '__main__':
    init()
    # tg.daily_msg()

    LOGGER.info(f"started, GIT_TAG={os.environ['GIT_TAG'] if 'GIT_TAG' in os.environ else ''}")
    LOGGER.info(f"target neo4j host: {config.get_string('neo4j', 'host')}")

    schedule.every(2).seconds.do(tg.get_updates)
    schedule.every().day.at("04:00").do(tg.monthly_stats)
    schedule.every().day.at("04:01").do(tg.daily_msg)

    config.reset()

    while 1:
        schedule.run_pending()
        time.sleep(1)

