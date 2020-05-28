from dao import eventdao
from entities.exceptions import EventError
from utils import log, ts

LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("event")


def find_by_event_id(tg_group_id, event_id, status):
    if not tg_group_id or not event_id:
        return None

    return eventdao.find_by_event_id(tg_group_id=tg_group_id, event_id=event_id, status=status)


def find_active(tg_group_id):
    if not tg_group_id:
        return None

    return eventdao.find_by_start(tg_group_id=tg_group_id, start=ts.get_utc_now_in_ms(), status=["ACTIVE"])


def take_attendance(tg_group_id, event_id, member_id, attendance, reason):
    if not tg_group_id or not event_id or not member_id or not attendance:
        return None
    if attendance not in ["GO", "NOT_GO", "NOT_SURE"]:
        raise EventError(f"invalid attendance({attendance})")

    eventdao.take_attendance(tg_group_id=tg_group_id, event_id=event_id, member_id=member_id, attendance=attendance, reason=str(reason).strip(), status=["ACTIVE"])
