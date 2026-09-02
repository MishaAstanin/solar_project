import datetime as dt
from pytz import UTC


def NOW():
    return dt.datetime.now().replace(tzinfo=UTC)

def make_aware(ts):
    return ts.replace(tzinfo=UTC)

# translates datetime instance into bigint (loses milliseconds), deprecated, use ts_float_resolver instead
# def ts_bigint_resolver(ts):
#     if ts.tzinfo is None:
#         ts = ts.replace(tzinfo=UTC)
#     return int(ts.timestamp())

def ts_float_resolver(ts):
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return float(ts.timestamp())

def float_ts_resolver(num):
    return dt.datetime.fromtimestamp(num, UTC)

def bigint_ts_resolver(num):
    return dt.datetime.fromtimestamp(num, UTC)

#q: any need to fix the pattern to include ms if provided? will it match to the dt if ms in not present in timestamp string?
#a: strptime requires exact format match. If ms are provided in the string but not in template, it will fail. Use optional ms pattern "%Y-%m-%d %H:%M:%S.%f" or handle with try/except for both formats.
def str_to_dt(st, template="%Y-%m-%d %H:%M:%S"):
    return dt.datetime.strptime(st, template)
