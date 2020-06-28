import uuid

from entities.exceptions import MemberError
from services import cache as simple_cache
from utils import log, ts
from dao import memberdao


LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("member")


def find_by_member_id(tg_group_id, member_id, status):
    if not tg_group_id or not member_id:
        return None

    key = f"member:{tg_group_id}:{member_id}"
    if cache := simple_cache.get(key):
        return cache

    db_members = memberdao.find_by_member_id(tg_group_id=tg_group_id, member_id=str(member_id), status=status)
    simple_cache.update(key, db_members)
    return db_members


def find_by_tg_id(tg_group_id, tg_id, status):
    if not tg_group_id or not tg_id:
        return None

    key = f"member:{tg_group_id}:{tg_id}"
    if cache := simple_cache.get(key):
        return cache

    db_members = memberdao.find_by_tg_id(tg_group_id=tg_group_id, tg_id=str(tg_id), status=status)
    simple_cache.update(key, db_members)
    return db_members


def find_by_type(tg_group_id, tg_id, mtype, status):
    if not mtype:
        return None

    if tg_group_id:
        key = f"members:{tg_group_id}:{mtype}"
        if cache := simple_cache.get(key):
            return cache

        db_members = memberdao.find_by_type(tg_group_id=tg_group_id, mtype=mtype, status=status)
        simple_cache.update(key, db_members)
        return db_members
    elif tg_id:
        # todo del this comment
        key = f"member:{tg_group_id}:{mtype}:{tg_id}"
        if cache := simple_cache.get(key):
            return cache

        db_members = memberdao.find_by_tg_id_and_type(tg_id=str(tg_id), mtype=mtype, status=status)
        simple_cache.update(key, db_members)
        return db_members
    else:
        return None


def find_by_name(tg_group_id, name: str, status):
    if not tg_group_id or not name:
        return None

    key = f"member:{tg_group_id}:{name}"
    if cache := simple_cache.get(key):
        return cache

    db_members = memberdao.find_by_name(tg_group_id=tg_group_id, name=name.lower().strip(), status=status)
    simple_cache.update(key, db_members)
    return db_members


def list(tg_group_id, mtypes, status):
    if not tg_group_id:
        return None

    key = f"members:{tg_group_id}"
    if cache := simple_cache.get(key):
        return cache

    db_members = memberdao.find(tg_group_id=tg_group_id, mtypes=mtypes, status=status)
    simple_cache.update(key, db_members)
    return db_members


def find_stats_by_member(tg_group_id, member_id, status):
    if not tg_group_id or not member_id:
        return None

    db_stats = memberdao.find_stats_by_member(tg_group_id=tg_group_id, member_id=member_id, status=status)
    return db_stats


def find_stats(tg_group_id, mtypes, status):
    if not tg_group_id or not mtypes:
        return None

    db_stats = memberdao.find_stats(tg_group_id=tg_group_id, exclude_mtypes=mtypes, status=status)
    attend_stats = sorted(db_stats, key=lambda item: item['attend_count'] / item['event_count'], reverse=True)
    attend_stats = '\n'.join([f"{i['member']['name']} ({i['attend_count']}/{i['event_count']})" for i in attend_stats])

    bring_stats = sorted(db_stats, key=lambda item: item['bring_count'] / item['event_count'], reverse=True)
    bring_stats = '\n'.join([f"{i['member']['name']} ({i['bring_count']}/{i['event_count']})" for i in bring_stats])

    get_stats = sorted(db_stats, key=lambda item: item['get_count'] / item['event_count'], reverse=True)
    get_stats = '\n'.join([f"{i['member']['name']} ({i['get_count']}/{i['event_count']})" for i in get_stats])

    db_stats = {
        'attend_stats': attend_stats,
        'bring_stats': bring_stats,
        'get_stats': get_stats,
    }
    return db_stats


def find_or_create_guest(tg_group_id, name: str, status):
    if not tg_group_id or not name:
        return None

    key = f"member:{tg_group_id}:{name}"
    if cache := simple_cache.get(key):
        return cache

    db_members = memberdao.find_by_name(tg_group_id=tg_group_id, name=name.lower().strip(), status=status)
    if db_members:
        db_members = db_members[0]
    else:
        db_members = create_guest(tg_group_id=tg_group_id, name=name)[0]

    simple_cache.update(key, db_members)

    return db_members


"""
    UPDATE 
"""


def create(tg_group_id, tg_id, name):
    if not tg_id or not tg_group_id or not name:
        raise MemberError(f"cannot create member, tg_id={tg_id}, tg_group_id={tg_group_id}, name={name}")

    memberdao.create({
      "tgGroupId": tg_group_id,
      "tgId": tg_id,
      "name": name,
      "type": "MEMBER",
      "uuid": str(uuid.uuid4()),
      "createAt": ts.get_utc_now_in_ms(),
      "updateAt": ts.get_utc_now_in_ms(),
      "status": "INACTIVE"
    })

    simple_cache.delete("members", bulk=True)


def create_guest(tg_group_id, name):
    if not tg_group_id or not name:
        raise MemberError(f"cannot create guest, tg_group_id={tg_group_id}, name={name}")

    return memberdao.create_guest({
      "tgGroupId": tg_group_id,
      "name": name,
      "type": "GUEST",
      "uuid": str(uuid.uuid4()),
      "createAt": ts.get_utc_now_in_ms(),
      "updateAt": ts.get_utc_now_in_ms(),
      "status": "ACTIVE"
    })


def update_status(tg_group_id, member_id, status):
    if not member_id or not tg_group_id:
        raise MemberError(f"cannot update member status, member_id={member_id}, tg_group_id={tg_group_id}")

    db_members = memberdao.update_status(tg_group_id=tg_group_id, member_id=member_id, status=status)
    simple_cache.delete("members", bulk=True)
    simple_cache.delete(f"member:{tg_group_id}:{member_id}")
    simple_cache.delete(f"member:{tg_group_id}:{db_members[0]['tgId']}")
    return db_members


def update_name(tg_group_id, member_id, name: str):
    if not member_id or not tg_group_id or not name:
        raise MemberError(f"cannot update member name, member_id={member_id}, tg_group_id={tg_group_id}")

    db_members = memberdao.update_name(tg_group_id=tg_group_id, member_id=member_id, name=name)
    simple_cache.delete("members", bulk=True)
    simple_cache.delete(f"member:{tg_group_id}:{member_id}")
    simple_cache.delete(f"member:{tg_group_id}:{db_members[0]['tgId']}")
    return db_members


def update_bday(tg_group_id, member_id, bday: str):
    if not member_id or not tg_group_id or len(bday) != 16:
        raise MemberError(f"cannot update member bday, member_id={member_id}, tg_group_id={tg_group_id}")

    bday = ts.to_milliseconds(bday)

    db_members = memberdao.update_bday(tg_group_id=tg_group_id, member_id=member_id, bday=bday)
    simple_cache.delete(f"member:{tg_group_id}:{member_id}")
    simple_cache.delete(f"member:{tg_group_id}:{db_members[0]['tgId']}")
    return db_members


def update_default_attendance(tg_group_id, member_id, attendance: str):
    if not member_id or not tg_group_id or attendance not in ["GO", "NOT_GO", "NOT_SURE"]:
        raise MemberError(f"cannot update member default attendance, member_id={member_id}, tg_group_id={tg_group_id}")

    db_members = memberdao.update_default_attendance(tg_group_id=tg_group_id, member_id=member_id, attendance=attendance)
    simple_cache.delete(f"member:{tg_group_id}:{member_id}")
    simple_cache.delete(f"member:{tg_group_id}:{db_members[0]['tgId']}")
    return db_members
