import uuid

from dao import eventdao, memberdao
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










def create(tg_group_id, event_id=''):
    if not tg_group_id:
        raise EventError(f"cannot create event, tg_group_id={tg_group_id}")

    # {
    #   "date": 1591200000000,
    #   "name": "練波啦喂😂",
    #   "updateAt": 1590908927455,
    #   "type": "GATHERING",
    #   "uuid": "ace4e2c9-eff0-494f-9ad3-7e5292eef4c6",
    #   "createAt": 1548086343683,
    #   "status": "ACTIVE"
    # }
    db_events = None
    if event_id:
        db_events = eventdao.find_by_id(tg_group_id=tg_group_id, event_id=event_id, status=["ACTIVE"])
        if db_events:
            db_events = db_events[0]

    if db_events:
        event = {
            "date": db_events['date'] + ts.ONE_WEEK_SECONDS * 1000,
            "name": db_events['name'] + "*",
            "type": db_events['type'],
            "uuid": str(uuid.uuid4()),
            "createAt": ts.get_utc_now_in_ms(),
            "updateAt": ts.get_utc_now_in_ms(),
            "status": "ACTIVE"
        }
    else:
        event = {
            "date": ts.get_utc_now_in_ms() + ts.ONE_WEEK_SECONDS * 1000,
            "name": "夠鐘執波了",
            "type": "PRACTICE",
            "uuid": str(uuid.uuid4()),
            "createAt": ts.get_utc_now_in_ms(),
            "updateAt": ts.get_utc_now_in_ms(),
            "status": "ACTIVE"
        }
    venue = eventdao.find_most_common_venues(tg_group_id=tg_group_id, status=["ACTIVE"])
    if venue:
        venue = venue[0]['name']
    else:
        venue = "唔知去邊"
    start_time = eventdao.find_most_common_start_time(tg_group_id=tg_group_id, status=["ACTIVE"])
    if start_time:
        start_time = start_time[0]['time']
    else:
        start_time = "00:00"
    end_time = eventdao.find_most_common_end_time(tg_group_id=tg_group_id, status=["ACTIVE"])
    if end_time:
        end_time = end_time[0]['time']
    else:
        end_time = "23:59"
    db_events = eventdao.create(tg_group_id=tg_group_id, event=event, start_time=start_time, end_time=end_time, venue=venue)
    event_id = db_events[0]['uuid']
    eventdao.take_attendance_by_default(tg_group_id=tg_group_id, event_id=event_id, attendance="GO", reason="", status=["ACTIVE"])
    eventdao.take_attendance_by_default(tg_group_id=tg_group_id, event_id=event_id, attendance="NOT_GO", reason="", status=["ACTIVE"])
    return eventdao.find_by_id(tg_group_id=tg_group_id, event_id=event_id, status=["ACTIVE"])


def take_attendance(tg_group_id, event_id, member_id, attendance, reason):
    if not tg_group_id or not event_id or not member_id or not attendance:
        return None
    if attendance not in ["GO", "NOT_GO", "NOT_SURE"]:
        raise EventError(f"invalid attendance({attendance})")

    return eventdao.take_attendance(tg_group_id=tg_group_id, event_id=event_id, member_id=member_id, attendance=attendance, reason=str(reason).strip(), status=["ACTIVE"])


def take_ball(tg_group_id, event_id, member_id, action):
    if not tg_group_id or not event_id or not member_id or not action:
        return None
    if action not in ["BRING", "GET"]:
        raise EventError(f"invalid action({action})")

    return eventdao.take_ball(tg_group_id=tg_group_id, event_id=event_id, member_id=member_id, action=action, status=["ACTIVE"])


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


def update_name(tg_group_id, event_id, name: str):
    if not event_id or not tg_group_id or not name:
        raise EventError(f"cannot update event name, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_name(tg_group_id=tg_group_id, event_id=event_id, name=name)


def update_venue(tg_group_id, event_id, venue: str):
    if not event_id or not tg_group_id or not venue:
        raise EventError(f"cannot update event venue, event_id={event_id}, tg_group_id={tg_group_id}")

    return eventdao.update_venue(tg_group_id=tg_group_id, event_id=event_id, venue=venue)
