import uuid

from entities.exceptions import MemberError
from utils import log, ts
from dao import memberdao


LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("member")


# def authorize(tg_id):

def find(tg_id, tg_group_id):
    return memberdao.find(tg_id, tg_group_id)


def find_by_member_type(tg_id, tg_group_id, member_type):
    if not member_type:
        return None

    if tg_group_id:
        return memberdao.find_by_member_type_and_tg_group_id(str(tg_group_id), member_type)
    elif tg_id:
        return memberdao.find_by_member_type_and_tg_id(str(tg_id), member_type)
    else:
        return None


def list_by_tg_group_id(tg_group_id):
    return memberdao.find_by_tg_group_id(tg_group_id)












def create(tg_id, tg_group_id, name):
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
