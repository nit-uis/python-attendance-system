import re

from neo4j import Driver
from utils import log
from db import neo4j


CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("memberdao")


def find(tg_group_id: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: $tg_group_id}) 
        WHERE member.status in $status
        RETURN member
        ORDER BY member.type ASC, member.createAt ASC
    """, {"tg_group_id": tg_group_id, "status": status})

    return [i['member'] for i in results]


def find_by_member_id(tg_group_id: str, member_id: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{uuid: $member_id, tgGroupId: $tg_group_id}) 
        WHERE member.status in $status
        RETURN member
    """, {"tg_group_id": tg_group_id, "member_id": member_id, "status": status})

    return [i['member'] for i in results]


def find_by_tg_id(tg_group_id: str, tg_id: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgId: $tg_id, tgGroupId: $tg_group_id})
        WHERE member.status in $status
        RETURN member
    """, {"tg_group_id": tg_group_id, "tg_id": tg_id, "status": status})

    return [i['member'] for i in results]


def find_by_name(tg_group_id: str, name: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: $tg_group_id}) 
        WHERE ToLower(member.name) = $name and member.status in $status
        RETURN member
    """, {"tg_group_id": tg_group_id, "name": name, "status": status})

    return [i['member'] for i in results]


# find members with specific member type in the same group
def find_by_type(tg_group_id: str, mtype: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{tgGroupId: $tg_group_id, type: $type}) 
        WHERE member.status in $status
        RETURN member
    """, {"tg_group_id": tg_group_id, "type": mtype, "status": status})

    return [i['member'] for i in results]


# find members with specific member type in the same group
def find_by_tg_id_and_type(tg_id: str, mtype: str, status: list):
    results = CLIENT.run("""
        MATCH (:TgMember{tgId: $tg_id})--(mg:TgMemberGroup{status: "ACTIVE"})
        MATCH (mg)--(member:TgMember{type: $type})
        WHERE member.status in $status
        RETURN member
    """, {"tg_id": tg_id, "type": mtype, "status": status})

    return [i['member'] for i in results]


def find_stats_by_member(tg_group_id: str, member_id: str, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember{uuid: $member_id})-[:JOIN]-(event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE member.status in $status and event.status in $status and memberGroup.status in $status
        OPTIONAL MATCH (member)-[gr{name:"GO"}]-(event)
        OPTIONAL MATCH (member)-[bbr{bring:true}]-(event)
        OPTIONAL MATCH (member)-[gbr{get:true}]-(event)
        RETURN DISTINCT count(DISTINCT event) as event_count, count(DISTINCT gr) as attend_count, count(DISTINCT bbr) as bring_count, count(DISTINCT gbr) as get_count
    """, {"tg_group_id": tg_group_id, "member_id": member_id, "status": status})

    return [i.data() for i in results]


def find_stats(tg_group_id: str, exclude_mtypes: list, status: list):
    results = CLIENT.run("""
        MATCH (member:TgMember)-[:JOIN]-(event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE member.status in $status and not member.type in $mtype and event.status in $status and memberGroup.status in $status
        OPTIONAL MATCH (member)-[gr{name:"GO"}]-(event)
        OPTIONAL MATCH (member)-[bbr{bring:true}]-(event)
        OPTIONAL MATCH (member)-[gbr{get:true}]-(event)
        RETURN DISTINCT member, count(DISTINCT event) as event_count, count(DISTINCT gr) as attend_count, count(DISTINCT bbr) as bring_count, count(DISTINCT gbr) as get_count
    """, {"tg_group_id": tg_group_id, "exclude_mtypes": exclude_mtypes, "status": status})

    return [i.data() for i in results]


"""
    UPDATE QUERY
"""


def create(member: dict):
    member_json = re.sub(r'\'(\w+)\':', r'\1:', str(member))
    LOGGER.debug(f"member_json={member_json}")

    CLIENT.run("MATCH (member_group:TgMemberGroup{tgGroupId: $tg_group_id, status: $status}) "
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
            MATCH (member:TgMember{tgGroupId: $tg_group_id, uuid: $member_id})
            SET member.status = $status, member.updateAt = timestamp()
            RETURN member
        """, {"tg_group_id": tg_group_id, "member_id": member_id, "status": status})

    return [i['member'] for i in results]


def update_bday(tg_group_id: str, member_id: str, bday: int):
    results = CLIENT.run("""
            MATCH (member:TgMember{uuid: $member_id, status: "ACTIVE", tgGroupId: $tg_group_id}) 
            SET member.bornAt = $bday, member.updateAt = timestamp()
            RETURN member
        """, {"tg_group_id": tg_group_id, "member_id": member_id, "bday": bday})

    return [i['member'] for i in results]


def update_name(tg_group_id: str, member_id: str, name: str):
    results = CLIENT.run("""
            MATCH (member:TgMember{uuid: $member_id, status: "ACTIVE", tgGroupId: $tg_group_id}) 
            SET member.name = $name, member.updateAt = timestamp()
            RETURN member
        """, {"tg_group_id": tg_group_id, "member_id": member_id, "name": name})

    return [i['member'] for i in results]


def update_default_attendance(tg_group_id: str, member_id: str, attendance: str):
    results = CLIENT.run("""
            MATCH (member:TgMember{uuid: $member_id, status: "ACTIVE", tgGroupId: $tg_group_id}) 
            SET member.defaultAttendance = $attendance, member.updateAt = timestamp()
            RETURN member
        """, {"tg_group_id": tg_group_id, "member_id": member_id, "attendance": attendance})

    return [i['member'] for i in results]
