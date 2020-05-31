from neo4j import Driver
from utils import ts, log
from db import neo4j

CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("eventdao")


def find_by_id(tg_group_id: str, event_id: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: {event_id}})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}}) 
        WHERE event.status in {status} and memberGroup.status in {status}
        MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        OPTIONAL MATCH (member:TgMember)-[r:JOIN]-(event)-[:HOLD_AT]-(venue:TgVenue)
        WHERE member.status in {status}
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "event_id": event_id, "status": status})

    return [i['event'] for i in results]


def find_by_date(tg_group_id: str, date: int, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}}) 
        WHERE event.status in {status} and {date} = event.date and memberGroup.status in {status}
        MATCH (member:TgMember)-[r:JOIN]-(event)-[:HOLD_AT]-(venue:TgVenue)
        WHERE member.status in {status}
        MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "date": date, "status": status})

    return [i['event'] for i in results]


def find_by_start(tg_group_id: str, start: int, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}}) 
        WHERE event.status in {status} and {start} < event.date and memberGroup.status in {status}
        MATCH (member:TgMember)-[r:JOIN]-(event)-[:HOLD_AT]-(venue:TgVenue)
        WHERE member.status in {status}
        MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "start": start, "status": status})

    return [i['event'] for i in results]


def find_by_start_and_end(tg_group_id: str, start: int, end: int, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}}) 
        WHERE event.status in {status} and {start} <= event.date < {end} and memberGroup.status in {status}
        MATCH (member:TgMember)-[r:JOIN]-(event)-[:HOLD_AT]-(venue:TgVenue)
        WHERE member.status in {status}
        MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "start": start, "end": end, "status": status})

    return [i['event'] for i in results]


def take_attendance(tg_group_id: str, event_id: str, member_id: str, attendance: str, reason: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: {event_id}})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}}) 
        WHERE event.status in {status} and memberGroup.status in {status} 
        MATCH (member:TgMember{uuid: {member_id}}) 
        WHERE member.status in {status} 
        MERGE (member)-[r:JOIN]->(event) 
        SET r.createAt = timestamp(), r.reason = {reason}, r.name = {attendance}
        RETURN member 
    """, {"tg_group_id": tg_group_id,
          "event_id": event_id,
          "member_id": member_id,
          "attendance": attendance,
          "reason": reason,
          "status": status})

    return [i['member'] for i in results]


def update_status(tg_group_id: str, event_id: str, status: list):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: {event_id}})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}, status:"ACTIVE"}) 
            SET event.status = {status}, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "status": status})

    return [i['event'] for i in results]


def update_start_time(tg_group_id: str, event_id: str, time: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: {event_id}, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}, status:"ACTIVE"}) 
            MATCH (event)-[:START_AT]-(time:TgTime)
            SET time.time = {time}, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "time": time})

    return [i['event'] for i in results]


def update_end_time(tg_group_id: str, event_id: str, time: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: {event_id}, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}, status:"ACTIVE"}) 
            MATCH (event)-[:END_AT]-(time:TgTime)
            SET time.time = {time}, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "time": time})

    return [i['event'] for i in results]


def update_type(tg_group_id: str, event_id: str, etype: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: {event_id}, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}, status:"ACTIVE"}) 
            SET event.type = {etype}, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "etype": etype})

    return [i['event'] for i in results]


def update_date(tg_group_id: str, event_id: str, date: int):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: {event_id}, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}, status:"ACTIVE"}) 
            SET event.date = {date}, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "date": date})

    return [i['event'] for i in results]


def update_venue(tg_group_id: str, event_id: str, venue: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: {event_id}, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: {tg_group_id}, status:"ACTIVE"}) 
            OPTIONAL MATCH (event)-[r:HOLD_AT]-(venue:TgVenue)
            DELETE r
            WITH event
            MERGE (event)-[:HOLD_AT]->(:TgVenue{name: {venue}})
            SET event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "venue": venue})

    return [i['event'] for i in results]
