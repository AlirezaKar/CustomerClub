from django.utils import timezone
import datetime as datetime_lib
import pytz

def now(seconds= 0, minutes= 0):
    tz= pytz.timezone(timezone.get_current_timezone_name())
    aware= tz.localize(datetime_lib.datetime.now(), is_dst= None)

    if minutes:
        aware+= datetime_lib.timedelta(minutes= minutes)
    if seconds:
        aware+= datetime_lib.timedelta(seconds= seconds)

    return aware
