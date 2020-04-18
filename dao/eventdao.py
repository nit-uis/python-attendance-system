from neo4j import Driver
from utils import ts, log
from db import neo4j

CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("eventdao")


