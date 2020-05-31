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


def find(tg_group_id: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: {tg_group_id}}) 
        WHERE member.status in {status}
        RETURN member
        ORDER BY member.type ASC, member.createAt ASC
    """, {"tg_group_id": tg_group_id, "status": status})

    return [i['member'] for i in results]


def find_by_tg_id(tg_group_id: str, tg_id: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgId: {tg_id}, tgGroupId: {tg_group_id}}) 
        WHERE member.status in {status}
        RETURN member
    """, {"tg_group_id": tg_group_id, "tg_id": tg_id, "status": status})

    return [i['member'] for i in results]


def find_by_name(tg_group_id: str, name: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: {tg_group_id}}) 
        WHERE lower(member.name) = {name} and member.status in {status}
        RETURN member
    """, {"tg_group_id": tg_group_id, "name": name, "status": status})

    return [i['member'] for i in results]


# find members with specific member type in the same group
def find_by_type(tg_group_id: str, mtype: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: {tg_group_id}, type: {type}}) 
        WHERE member.status in {status}
        RETURN member
    """, {"tg_group_id": tg_group_id, "type": mtype, "status": status})

    return [i['member'] for i in results]


# find members with specific member type in the same group
def find_by_tg_id_and_type(tg_id: str, mtype: str, status: list):
    results = CLIENT.run("""
        MATCH (:TgMember{tgId: {tg_id}})--(mg:TgMemberGroup{status: "ACTIVE"})
        MATCH (mg)--(member:TgMember{type: {type}})
        WHERE member.status in {status}
        RETURN member
    """, {"tg_id": tg_id, "type": mtype, "status": status})

    return [i['member'] for i in results]


"""
    UPDATE QUERY
"""


def create(member: dict):
    member_json = re.sub(r'\'(\w+)\':', r'\1:', str(member))
    LOGGER.debug(f"member_json={member_json}")

    CLIENT.run("MATCH (member_group:TgMemberGroup{tgGroupId: {tg_group_id}, status: {status}}) "
               f"CREATE (member:TgMember{member_json}) "
               f"MERGE (member_group)-[:HAS]->(member) ",
               {"tg_group_id": member['tgGroupId'], "status": "ACTIVE"})


def create_guest(member: dict):
    member_json = re.sub(r'\'(\w+)\':', r'\1:', str(member))
    LOGGER.debug(f"member_json={member_json}")

    results = CLIENT.run(f"CREATE (member:TgMember{member_json}) RETURN member",
               {"tg_group_id": member['tgGroupId'], "status": "ACTIVE"})

    return [i['member'] for i in results]


def update_status(tg_group_id: str, member_id: str, status: list):
    results = CLIENT.run("""
            MATCH (member:TgMember{tgGroupId: {tg_group_id}, uuid: {member_id}})
            SET member.status = {status}, member.updateAt = timestamp()
            RETURN member
        """, {"tg_group_id": tg_group_id, "member_id": member_id, "status": status})

    return [i['member'] for i in results]
