from __future__ import absolute_import

import errno
import math
import os
import resource
import subprocess
import time
from functools import wraps

from .builtins import LuaTable, _lua, to_string, to_number


def catch_os_error(func):
    @wraps(func)
    def wrapper(*args):
        try:
            return func(*args)
        except OSError as e:
            return None, e.strerror, float(e.errno)

    return wrapper


def os_clock():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def os_date(format=None, time=None):
    if format is None:
        format = "%c"

    format = to_string(number)

    if format != "*t":
        return time.strftime(format, time)

    if time is not None:
        time = to_number(time)

    t = time.localtime(time)

    return LuaTable(
        { "year":   float(t.tm_year),
          "month":  float(t.tm_month),
          "day":    float(t.tm_mday),
          "hour":   float(t.tm_hour),
          "min":    float(t.tm_min),
          "sec":    float(t.tm_sec),
          "wday":   float(t.tm_wday),
          "yday":   float(t.tm_yday),
          "isdst":  bool(t.tm_isdst),
          })


def os_difftime(t2, t1):
    return to_number(t2) - to_number(t1)


def os_execute(command=None):
    if command is None:
        return True

    command = to_string(command)

    p = subprocess.Popen(command, shell=True)
    result = p.wait()
    if result == 0:
        return True, 'exit', 0.0

    elif result > 0:
        return None, 'exit', float(result)

    return None, 'signal', float(-result)


def os_exit(code=True):
    if code is True:
        exit()
    elif code is False:
        exit(1)

    exit(to_number(code))


def os_getenv(varname):
    return os.environ.get(
        to_string(varname),
        None)


def os_remove(filename):
    filename = to_string(filename)

    try:
        os.remove(filename)
        return True
    except OSError as e:
        if e.errno != errno.EISDIR:
            raise e

    os.rmdir(filename)
    return True


def os_rename(oldname, newname):
    os.rename(
        to_string(oldname),
        to_string(newname))
    return True


def os_time(table=None):
    if table is None:
        return math.floor(time.time())

    return time.mktime(
        ( int(to_number(table.data["year"])),
          int(to_number(table.data["month"])),
          int(to_number(table.data["day"])),
          int(to_number(table.data.get("hour", 12.0))),
          int(to_number(table.data.get("min", 0.0))),
          int(to_number(table.data.get("sec", 0.0))),
          0,
          0,
          int(to_number(table.data.get("isdst", -1.0)))))



mod_os = LuaTable({
    'clock':     _lua(1)(os_clock),
    'date':      _lua(1)(os_date),
    'difftime':  _lua(1)(os_difftime),
    'execute':   os_execute,
    'exit':      _lua()(os_exit),
    'getenv':    _lua(1)(os_getenv),
    'remove':    catch_os_error(_lua(1)(os_remove)),
    'rename':    catch_os_error(_lua(1)(os_rename)),
    'time':      _lua(1)(os_time),
})
