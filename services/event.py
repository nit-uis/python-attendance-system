from dao import eventdao
from entities.exceptions import EventError
from utils import log, ts

LOGGER = None


def init():
    global LOGGER
    LOGGER = log.get_logger("event")


def find_by_id(tg_group_id, event_id, status):
    if not tg_group_id or not event_id:
        return None

    return eventdao.find_by_id(tg_group_id=tg_group_id, event_id=event_id, status=status)


# date in format yyyy-MM-dd +0800
def find_by_date(tg_group_id, date: str, status):
    if not tg_group_id or not date or len(date) != 16:
        return None

    start = ts.to_milliseconds(date)
    end = (start + (ts.ONE_DAY_SECONDS + 1) * 1000)
    print(start, end)

    return eventdao.find_by_start_and_end(tg_group_id=tg_group_id, start=start, end=end, status=status)


def find_coming(tg_group_id):
    if not tg_group_id:
        return None

    return eventdao.find_by_start(tg_group_id=tg_group_id, start=ts.get_utc_now_in_ms(), status=["ACTIVE"])


def take_attendance(tg_group_id, event_id, member_id, attendance, reason):
    if not tg_group_id or not event_id or not member_id or not attendance:
        return None
    if attendance not in ["GO", "NOT_GO", "NOT_SURE"]:
        raise EventError(f"invalid attendance({attendance})")

    eventdao.take_attendance(tg_group_id=tg_group_id, event_id=event_id, member_id=member_id, attendance=attendance, reason=str(reason).strip(), status=["ACTIVE"])


def update_status(tg_group_id, event_id, status):
    if not event_id or not tg_group_id:
        raise EventError(f"cannot update event status, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_status(tg_group_id=tg_group_id, event_id=event_id, status=status)


def update_start_time(tg_group_id, event_id, start_time):
    if not event_id or not tg_group_id or not start_time:
        raise EventError(f"cannot update event start time, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_start_time(tg_group_id=tg_group_id, event_id=event_id, time=start_time)


def update_end_time(tg_group_id, event_id, end_time):
    if not event_id or not tg_group_id or not end_time:
        raise EventError(f"cannot update event end time, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_end_time(tg_group_id=tg_group_id, event_id=event_id, time=end_time)


def update_type(tg_group_id, event_id, etype):
    if not event_id or not tg_group_id or not etype:
        raise EventError(f"cannot update event type, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_type(tg_group_id=tg_group_id, event_id=event_id, etype=etype)


def update_date(tg_group_id, event_id, date: str):
    if not event_id or not tg_group_id or len(date) != 16:
        raise EventError(f"cannot update event date, event_id={event_id}, tg_group_id={tg_group_id}")

    date = ts.to_milliseconds(date)

    return eventdao.update_date(tg_group_id=tg_group_id, event_id=event_id, date=date)


def update_venue(tg_group_id, event_id, venue: str):
    if not event_id or not tg_group_id or not venue:
        raise EventError(f"cannot update event venue, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_venue(tg_group_id=tg_group_id, event_id=event_id, venue=venue)
