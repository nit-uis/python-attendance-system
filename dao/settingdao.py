from neo4j import Driver
from utils import log
from db import neo4j


CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("settingdao")


def get(name):
    results = CLIENT.run("MATCH (setting:Setting{name: {name}}) RETURN setting",
                         {"name": name})
    for i in results:
        return i['setting']


def create_or_update_setting(vod_type, site_keys):
    CLIENT.run("MERGE (setting:CronJobSetting{name: {name}, type: {vod_type}}) "
               "SET setting.site_keys = {site_keys} ",
               {"name": "itunes-cron", "vod_type": vod_type, "site_keys": site_keys})
