import re
from datetime import datetime, timezone
from time import time

ONE_MINUTE_SECONDS = 60
ONE_HOUR_SECONDS = ONE_MINUTE_SECONDS * 60
ONE_DAY_SECONDS = ONE_HOUR_SECONDS * 24
EIGHT_HOUR_SECONDS = ONE_HOUR_SECONDS * 8
ONE_MONTH_SECONDS = ONE_DAY_SECONDS * 30

END_DATE_FORMAT = '%Y-%m-%d %z'
DATE_WITH_WEEK_FORMAT = '%Y-%m-%d (%a)'
LOCAL_DATE_FORMAT = '%Y-%m-%d'


# using
# local run & dev/uat run on cloud: the same timestamp
def to_seconds(str, format=END_DATE_FORMAT):
    try:
        return int('%.0f' % (datetime.strptime(str, format).timestamp()))
    except Exception as e:
        return 0


def to_milliseconds(str, format=END_DATE_FORMAT):
    return to_seconds(str, format) * 1000


# from hkt
# for ts without zone info
def to_milliseconds_utc(str, format=END_DATE_FORMAT):
    return (to_seconds(str, format) - EIGHT_HOUR_SECONDS) * 1000


def get_second_by_year(year):
    try:
        return to_seconds(f"{year.strip()}-01-01 +0000", END_DATE_FORMAT)
    except Exception as e:
        return 0


def get_second_range(time_second, interval_second):
    return int(time_second-interval_second), int(time_second+interval_second)


def fromUtcnowToString(format):
    return datetime.utcfromtimestamp(time()).strftime(format)


def is_milliseconds(ts):
    ts = str(ts).strip()
    return len(ts) > 11


def to_string(ts, format=END_DATE_FORMAT):
    if is_milliseconds(ts):
        return datetime.utcfromtimestamp(ts / 1000).strftime(format)
    else:
        return datetime.utcfromtimestamp(ts).strftime(format)


def to_string_hkt(ts, format=END_DATE_FORMAT):
    if is_milliseconds(ts):
        return to_string(ts + EIGHT_HOUR_SECONDS * 1000, format)
    else:
        return to_string(ts + EIGHT_HOUR_SECONDS, format)


def compareTimestampWithUtcnow(ts):
    return (datetime.utcnow()-ts).seconds

def getUtcnowTs():
    return datetime.utcnow()

# def getUtcnowMillis():
#     return int('%.0f'%(datetime.utcnow().timestamp() * 1000))


# this is utc time on cloud server while it is utc - 8 time on localhost server DLLM
def getUtcnowSeconds():
    return int('%.0f'%(datetime.utcnow().timestamp()))


# this is utc time on cloud server while it is utc - 8 time on localhost server DLLM
def get_utc_now_in_ms():
    return int('%.0f'%(datetime.utcnow().timestamp())) * 1000


# this is hk time on cloud server while it is utc time on localhost server DLLM
def getHknowSeconds():
    return getUtcnowSeconds() + 60*60*8



if __name__ == "__main__":
    print(f'current getUtcnowTs={getUtcnowTs()}, getUtcnowSeconds={getUtcnowSeconds()}, getHknowSeconds={getHknowSeconds()}')
    print(to_seconds("2019/09/09 19:50 +0800", "%Y/%m/%d %H:%M %z"))

