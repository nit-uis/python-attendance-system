import re
import textwrap

from neo4j import Driver
from utils import log
from db import neo4j

CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("eventdao")


def find_by_id(tg_group_id: str, event_id: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: $event_id})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status
        OPTIONAL MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        OPTIONAL MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        OPTIONAL MATCH (member:TgMember)-[r:JOIN]-(event)
        WHERE member.status in $status
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "event_id": event_id, "status": status})

    return [i['event'] for i in results]


def find_by_date(tg_group_id: str, date: int, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and $date = event.date and memberGroup.status in $status
        OPTIONAL MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        OPTIONAL MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        OPTIONAL MATCH (member:TgMember)-[r:JOIN]-(event)
        WHERE member.status in $status
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "date": date, "status": status})

    return [i['event'] for i in results]


def find_by_start(tg_group_id: str, start: int, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and $start < event.date and memberGroup.status in $status
        OPTIONAL MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        OPTIONAL MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        OPTIONAL MATCH (member:TgMember)-[r:JOIN]-(event)
        WHERE member.status in $status
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
        ORDER BY event.date ASC
    """, {"tg_group_id": tg_group_id, "start": start, "status": status})

    return [i['event'] for i in results]


def find_by_start_and_end(tg_group_id: str, start: int, end: int, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and $start <= event.date < $end and memberGroup.status in $status
        OPTIONAL MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        OPTIONAL MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        OPTIONAL MATCH (member:TgMember)-[r:JOIN]-(event)
        WHERE member.status in $status
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
    """, {"tg_group_id": tg_group_id, "start": start, "end": end, "status": status})

    return [i['event'] for i in results]


def find_event_types(tg_group_id: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status
        RETURN DISTINCT event.type as etype    
        ORDER BY event.type ASC
    """, {"tg_group_id": tg_group_id, "status": status})

    return [i['etype'] for i in results]


def find_by_event_type(tg_group_id: str, etype: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{type: $etype})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status
        OPTIONAL MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        OPTIONAL MATCH (end:TgTime)-[:END_AT]-(event)-[:START_AT]-(start:TgTime)
        OPTIONAL MATCH (member:TgMember)-[r:JOIN]-(event)
        WHERE member.status in $status
        RETURN event{.*, start: start.time, end: end.time, venue: venue.name, members: collect(DISTINCT member{.*, attendance:r{.*}})}     
        ORDER BY event.date ASC
    """, {"tg_group_id": tg_group_id, "etype": etype, "status": status})

    return [i['event'] for i in results]


def find_most_common_venues(tg_group_id, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status
        MATCH (event)-[:HOLD_AT]-(venue:TgVenue)
        RETURN DISTINCT venue{.*, count: count(DISTINCT event.uuid)}
        ORDER BY venue.count DESC
    """, {"tg_group_id": tg_group_id, "status": status})

    return [i['venue'] for i in results]


def find_most_common_start_time(tg_group_id, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status
        MATCH (event)-[:START_AT]-(time:TgTime)
        RETURN DISTINCT time{.*, count: count(DISTINCT event.uuid)}
        ORDER BY time.count DESC
    """, {"tg_group_id": tg_group_id, "status": status})

    return [i['time'] for i in results]


def find_most_common_end_time(tg_group_id, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent)--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status
        MATCH (event)-[:END_AT]-(time:TgTime)
        RETURN DISTINCT time{.*, count: count(DISTINCT event.uuid)}
        ORDER BY time.count DESC
    """, {"tg_group_id": tg_group_id, "status": status})

    return [i['time'] for i in results]


"""
    UPDATE QUERY
"""


def create(tg_group_id: str, event: dict, start_time: str, end_time: str, venue: str):
    event_json = re.sub(r'\'(\w+)\':', r'\1:', str(event))
    LOGGER.debug(f"event_json={event_json}")

    results = CLIENT.run(
        "MATCH (member_group:TgMemberGroup{tgGroupId: $tg_group_id, status: $status}) "
        + f"CREATE (event:TgEvent{event_json}) "
        + textwrap.dedent("""
            MERGE (member_group)-[:HAS]->(event) 
            WITH event 
            MERGE (event)-[:HOLD_AT]->(venue:TgVenue{name: $venue}) 
            WITH event 
            MERGE (event)-[:START_AT]->(start:TgTime{time: $start_time}) 
            WITH event 
            MERGE (event)-[:END_AT]->(end:TgTime{time: $end_time}) 
            RETURN event
    """), {"tg_group_id": tg_group_id, "start_time": start_time, "end_time": end_time, "venue": venue,
           "status": "ACTIVE"})

    return [i['event'] for i in results]


def take_attendance(tg_group_id: str, event_id: str, member_id: str, attendance: str, reason: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: $event_id})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status 
        MATCH (member:TgMember{uuid: $member_id}) 
        WHERE member.status in $status 
        MERGE (member)-[r:JOIN]->(event) 
        SET r.createAt = timestamp(), r.reason = $reason, r.name = $attendance
        RETURN event 
    """, {"tg_group_id": tg_group_id,
          "event_id": event_id,
          "member_id": member_id,
          "attendance": attendance,
          "reason": reason,
          "status": status})
    print({"tg_group_id": tg_group_id,
          "event_id": event_id,
          "member_id": member_id,
          "attendance": attendance,
          "reason": reason,
          "status": status})

    return [i['event'] for i in results]


def take_attendance_by_default(tg_group_id: str, event_id: str, attendance: str, reason: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: $event_id})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status 
        MATCH (member:TgMember)--(memberGroup)
        WHERE member.status in $status and member.defaultAttendance = $attendance
        MERGE (member)-[r:JOIN]->(event)
        SET r.name = $attendance, r.reason = $reason, r.createAt = timestamp(), r.bring = false, r.get = false
        RETURN event  
    """, {"tg_group_id": tg_group_id,
          "event_id": event_id,
          "attendance": attendance,
          "reason": reason,
          "status": status})

    return [i['event'] for i in results]


def reset_attendance(tg_group_id: str, event_id: str, attendance: str, reason: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: $event_id})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status 
        MATCH (member:TgMember)--(memberGroup)
        WHERE member.status in $status 
        MERGE (member)-[r:JOIN]->(event)
        SET r.name = $attendance, r.reason = $reason, r.createAt = timestamp(), r.bring = false, r.get = false
        RETURN event  
    """, {"tg_group_id": tg_group_id,
          "event_id": event_id,
          "attendance": attendance,
          "reason": reason,
          "status": status})

    return [i['event'] for i in results]


def take_ball(tg_group_id: str, event_id: str, member_id: str, action: str, status: list):
    results = CLIENT.run("""
        MATCH (event:TgEvent{uuid: $event_id})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id}) 
        WHERE event.status in $status and memberGroup.status in $status 
        MATCH (member:TgMember{uuid: $member_id}) 
        WHERE member.status in $status 
        MATCH (member)-[r:JOIN]->(event)
    """ + f" SET r.{action} = not r.{action} RETURN member"
                         , {"tg_group_id": tg_group_id,
                            "event_id": event_id,
                            "member_id": member_id,
                            "status": status})

    return [i['member'] for i in results]


def update_status(tg_group_id: str, event_id: str, status: list):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            SET event.status = $status, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "status": status})

    return [i['event'] for i in results]


def update_start_time(tg_group_id: str, event_id: str, time: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            MATCH (event)-[:START_AT]-(time:TgTime)
            SET time.time = $time, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "time": time})

    return [i['event'] for i in results]


def update_end_time(tg_group_id: str, event_id: str, time: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            MATCH (event)-[:END_AT]-(time:TgTime)
            SET time.time = $time, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "time": time})

    return [i['event'] for i in results]


def update_type(tg_group_id: str, event_id: str, etype: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            SET event.type = $etype, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "etype": etype})

    return [i['event'] for i in results]


def update_date(tg_group_id: str, event_id: str, date: int):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            SET event.date = $date, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "date": date})

    return [i['event'] for i in results]


def update_name(tg_group_id: str, event_id: str, name: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            SET event.name = $name, event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "name": name})

    return [i['event'] for i in results]


def update_venue(tg_group_id: str, event_id: str, venue: str):
    results = CLIENT.run("""
            MATCH (event:TgEvent{uuid: $event_id, status: "ACTIVE"})--(memberGroup:TgMemberGroup{tgGroupId: $tg_group_id, status:"ACTIVE"}) 
            OPTIONAL MATCH (event)-[r:HOLD_AT]-(venue:TgVenue)
            DELETE r
            WITH event
            MERGE (event)-[:HOLD_AT]->(:TgVenue{name: $venue})
            SET event.updateAt = timestamp()
            RETURN event
        """, {"tg_group_id": tg_group_id, "event_id": event_id, "venue": venue})

    return [i['event'] for i in results]
