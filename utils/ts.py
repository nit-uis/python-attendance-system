import re
from datetime import datetime, timezone
from time import time

ONE_MINUTE_SECONDS = 60
ONE_HOUR_SECONDS = ONE_MINUTE_SECONDS * 60
ONE_DAY_SECONDS = ONE_HOUR_SECONDS * 24
ONE_MONTH_SECONDS = ONE_DAY_SECONDS * 30

END_DATE_FORMAT = '%Y-%m-%d %z'


# using
# local run & dev/uat run on cloud: the same timestamp
def fromStringToSeconds(str, format=END_DATE_FORMAT):
    try:
        return int('%.0f' % (datetime.strptime(str, format).timestamp()))
    except Exception as e:
        return 0


def get_second_by_year(year):
    try:
        return fromStringToSeconds(f"{year.strip()}-01-01 +0000", END_DATE_FORMAT)
    except Exception as e:
        return 0


def get_second_range(time_second, interval_second):
    return int(time_second-interval_second), int(time_second+interval_second)


def fromUtcnowToString(format):
    return datetime.utcfromtimestamp(time()).strftime(format)


def compareTimestampWithUtcnow(ts):
    return (datetime.utcnow()-ts).seconds

def getUtcnowTs():
    return datetime.utcnow()

# def getUtcnowMillis():
#     return int('%.0f'%(datetime.utcnow().timestamp() * 1000))


# this is utc time on cloud server while it is utc - 8 time on localhost server DLLM
def getUtcnowSeconds():
    return int('%.0f'%(datetime.utcnow().timestamp()))


# this is hk time on cloud server while it is utc time on localhost server DLLM
def getHknowSeconds():
    return getUtcnowSeconds() + 60*60*8



if __name__ == "__main__":
    print(f'current getUtcnowTs={getUtcnowTs()}, getUtcnowSeconds={getUtcnowSeconds()}, getHknowSeconds={getHknowSeconds()}')
    print(fromStringToSeconds("2019/09/09 19:50 +0800", "%Y/%m/%d %H:%M %z"))

