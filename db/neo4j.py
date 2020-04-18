from neo4j import GraphDatabase
from configs import config
from utils import log

DRIVER: GraphDatabase.driver
LOGGER = None


def init():
    global DRIVER, LOGGER
    neo4j_host = config.get_string("neo4j", "host")
    neo4j_user = config.get_string("neo4j", "user")
    neo4j_password = config.get_string("neo4j", "password")

    DRIVER = GraphDatabase.driver(neo4j_host, auth=(neo4j_user, neo4j_password))
    LOGGER = log.get_logger("neo4j")
    LOGGER.info(f"connected to {neo4j_host}")
