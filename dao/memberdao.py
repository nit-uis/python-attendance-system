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
        MATCH (member:TgMember{tgId: {tg_id}, tgGroupId: {tg_group_id}, status: "ACTIVE"}) 
        RETURN member
    """, {"tg_id": tg_id, "tg_group_id": tg_group_id})

    # return the first one
    for i in results:
        LOGGER.debug(i['member'])
        return i['member']


def find_by_tg_group_id(tg_group_id):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: {tg_group_id}, status: "ACTIVE"}) 
        RETURN member
        ORDER BY member.type ASC, member.createAt ASC
    """, {"tg_group_id": tg_group_id})

    return [i['member'] for i in results]


# find members with specific member type in the same group
def find_by_member_type_and_tg_group_id(tg_group_id, member_type):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: {tg_group_id}, member_type: {member_type}, status: "ACTIVE"}) 
        RETURN member
    """, {"tg_group_id": tg_group_id, "member_type": member_type})

    return [i['member'] for i in results]


# find members with specific member type in the same group
def find_by_member_type_and_tg_id(tg_id, member_type):
    results = CLIENT.run("""
        MATCH (:TgMember{tgId: {tg_id}})--(mg:TgMemberGroup{status: "ACTIVE"})
        MATCH (mg)--(member:TgMember{type: {member_type}, status: "ACTIVE"})
        RETURN member
    """, {"tg_id": tg_id, "member_type": member_type})

    return [i['member'] for i in results]


# [i['movie_id'] for i in results]


def create(member: dict):
    member_json = re.sub(r'\'(\w+)\':', r'\1:', str(member))
    LOGGER.debug(f"member_json={member_json}")

    CLIENT.run("MATCH (member_group:TgMemberGroup{tgGroupId: {tg_group_id}, status: {status}}) "
               f"CREATE (member:TgMember{member_json}) "
               f"MERGE (member_group)-[:HAS]->(member) ",
               {"tg_group_id": member['tgGroupId'], "status": "ACTIVE"})

