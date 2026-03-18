import datetime as dt
from pytz import UTC

# time work
def NOW():
    return dt.datetime.now().replace(tzinfo=UTC)

def make_aware(ts):
    return ts.replace(tzinfo=UTC)

# translates datetime instance into bigint
def ts_bigint_resolver(ts):
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return int(ts.timestamp())
    
# translates number into the datetime instance
def bigint_ts_resolver(num):
    return dt.datetime.fromtimestamp(num, UTC)

def str_to_dt(st, template="%Y-%m-%d %H:%M:%S"):
    return dt.datetime.strptime(st, template)
