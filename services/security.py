from entities.exceptions import Unauthorized
from services.member import find_by_tg_id
from utils import log

LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("member")


def is_admin(member):
    return 'type' in member and "ADMIN" in member['type']


def authorize(tg_group_id, tg_id):
    db_members = find_by_tg_id(tg_group_id=tg_group_id, tg_id=tg_id, status=["ACTIVE"])
    if not db_members or db_members[0]['type'] not in ["MEMBER", "ADMIN", "COACH", "SUPER_ADMIN"]:
        raise Unauthorized(f"{tg_id} is trying to access")

    return db_members[0]


def authorize_admin(member):
    if 'type' not in member or "ADMIN" not in member['type']:
        raise Unauthorized(f"{member['name']} is trying to access")
