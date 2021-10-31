from datetime import datetime
from datetime import timedelta

def nowUtcIsoFormat():
    dt = datetime.utcnow()
    return dt.isoformat()

def dateTimeFromUtcIsoFormat(str_dt):
    dt, _, us = str_dt.partition(".")
    dt = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    us = int(us.rstrip("Z"), 10)
    return dt + timedelta(microseconds=us)

def nowUTC():
    return datetime.now()

def delta_seconds_iso(old_str, new_str):
    new = dateTimeFromUtcIsoFormat(new_str)
    old = dateTimeFromUtcIsoFormat(old_str)
    diff = new - old
    return diff.seconds

def delta_seconds_str(old_str, new_str, format='%d-%m-%Y %H:%M:%S'):
    new = datetime.strptime(new_str, format)
    old = datetime.strptime(old_str, format)
    diff = new - old
    return diff.seconds


def formatDateTime(dt, format='%d-%m-%Y %H:%M'):
    if dt:
        return dt.strftime(format)
    return None

def timestamp_yyyymmdd():
    return nowUTC().strftime("%Y%m%d")


def delta_min(dt1, dt2):
    diff = dt2 - dt1
    min_sec = divmod(diff.days * 86400 + diff.seconds, 60) # (min,sec)
    return min_sec[0]

def delta_days(dt1, dt2):
    diff = dt2 - dt1
    return diff.days

def getTime(time_str, format='%H:%M'):
    try:
        return datetime.strptime(time_str, format)
    except ValueError:
        return None

def formatTime(dt, format='%H:%M'):
    return dt.strftime(format)

def convertSecondsInHourMinString(seconds):
    import time
    hh, mm, sec = [int(x) for x in time.strftime('%H:%M:%S', time.gmtime(seconds)).split(':')]
    if sec >= 30:
        mm += 1
    if hh:
        return '{} ora {} minuti'.format(hh, mm)
    else:
        return '{} minuti'.format(mm)

def getDatetime(date_string, format='%d%m%Y'):
    try:
        date = datetime.strptime(date_string, format)
    except ValueError:
        return None
    return date

def removeTimezone(dt):
    return dt.replace(tzinfo=None)

def getMinutes(input):
    t1 = datetime.strptime(input, '%H:%M')
    t2 = datetime.strptime('00:00', '%H:%M')
    return int((t1-t2).total_seconds()//60)

def get_date_tomorrow(dt):
    return dt + timedelta(days=1)

