import uuid

from entities.exceptions import MemberError
from utils import log, ts
from dao import memberdao


LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("member")


def find(tg_id, tg_group_id):
    return memberdao.find(tg_id, tg_group_id)


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
