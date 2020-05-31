import uuid

from entities.exceptions import MemberError
from utils import log, ts
from dao import memberdao


LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("member")


def is_admin(mtype):
    return "ADMIN" in mtype


def find_by_tg_id(tg_group_id, tg_id, status):
    if not tg_group_id or not tg_id:
        return None

    return memberdao.find_by_tg_id(tg_group_id=tg_group_id, tg_id=str(tg_id), status=status)


def find_by_type(tg_group_id, tg_id, mtype, status):
    if not mtype:
        return None

    if tg_group_id:
        return memberdao.find_by_type(tg_group_id=tg_group_id, mtype=mtype, status=status)
    elif tg_id:
        return memberdao.find_by_tg_id_and_type(tg_id=str(tg_id), mtype=mtype, status=status)
    else:
        return None


def find_by_name(tg_group_id, name: str, status):
    if not tg_group_id or not name:
        return None

    return memberdao.find_by_name(tg_group_id=tg_group_id, name=name.lower().strip(), status=status)


def find_or_create_guest(tg_group_id, name: str, status):
    if not tg_group_id or not name:
        return None

    db_members = memberdao.find_by_name(tg_group_id=tg_group_id, name=name.lower().strip(), status=status)
    if db_members:
        return db_members[0]
    else:
        return create_guest(tg_group_id=tg_group_id, name=name)[0]


def list(tg_group_id, status):
    if not tg_group_id:
        return None

    return memberdao.find(tg_group_id=tg_group_id, status=status)












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

    return memberdao.update_status(tg_group_id=tg_group_id, member_id=member_id, status=status)
