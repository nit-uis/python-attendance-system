import re

from neo4j import Driver
from utils import ts, log
from db import neo4j

CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("memberdao")


def find(tg_id, tg_group_id):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgId: {tg_id}, tgGroupId: {tg_group_id}}) 
        RETURN member
    """, {"tg_id": tg_id, "tg_group_id": tg_group_id})

    # return the first one
    for i in results:
        LOGGER.debug(i['member'])
        return i['member']


def find_by_member_type(tg_group_id, member_type):
    results = CLIENT.run("MATCH (member:TgMember{tgGroupId: {tg_group_id}, member_type: {member_type}, status: {status}}) "
                         "RETURN member",
                         {"tg_group_id": tg_group_id, "member_type": member_type, "status": "ACTIVE"})

    # return the first one
    for i in results:
        LOGGER.debug(i['member'])
        return i['member']


# [i['movie_id'] for i in results]


def create(member: dict):
    member_json = re.sub(r'\'(\w+)\':', r'\1:', str(member))
    LOGGER.debug(f"member_json={member_json}")

    CLIENT.run("MATCH (member_group:TgMemberGroup{tgGroupId: {tg_group_id}, status: {status}}) "
               f"CREATE (member:TgMember{member_json}) "
               f"MERGE (member_group)-[:HAS]->(member) ",
               {"tg_group_id": member['tgGroupId'], "status": "ACTIVE"})

