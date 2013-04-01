from __future__ import absolute_import

import math
import random
from functools import wraps

from .builtins import LuaTable, _lua, to_number


def _1(func):
    @wraps(func)
    def wrapper(x):
        x = to_number(x)

        try:
            return func(x)
        except OverflowError:
            return float("inf")
        except ValueError:
            return float("nan")
            
    return wrapper


def _2(func):
    @wraps(func)
    def wrapper(x, y):
        x = to_number(x)
        y = to_number(y)

        try:
            return func(x, y)
        except OverflowError:
            return float("inf")
        except ValueError:
            return float("nan")

    return wrapper


def math_log(x, base=None):
    try:
        if base is not None:
            base = to_number(base)

        return math.log(x, base)
    except OverflowError:
        return float("inf")
    except ValueError:
        return float("nan")


def math_max(*args):
    return max(map(to_number, args))


def math_min(*args):
    return min(map(to_number, args))


def math_random(m=None, n=None):
    if m is None and n is None:
        return random.random()

    if n is None:
        n = m
        m = 1.0

    return random.randint(
        math.floor(to_number(m)),
        math.floor(to_number(n)))


mod_math = LuaTable({
    'abs':         _lua(1)(_1(abs)),
    'acos':        _lua(1)(_1(math.acos)),
    'asin':        _lua(1)(_1(math.asin)),
    'atan':        _lua(1)(_1(math.atan)),
    'atan2':       _lua(1)(_2(math.atan2)),
    'ceil':        _lua(1)(_1(math.ceil)),
    'cos':         _lua(1)(_1(math.cos)),
    'cosh':        _lua(1)(_1(math.cosh)),
    'deg':         _lua(1)(_1(math.degrees)),
    'exp':         _lua(1)(_1(math.exp)),
    'floor':       _lua(1)(_1(math.floor)),
    'fmod':        _lua(1)(_2(math.fmod)),
    'frexp':       _lua(1)(_1(math.frexp)),
    'huge':        float('inf'),
    'ldexp':       _lua(1)(_2(math.ldexp)),
    'log':         _lua(1)(math_log),
    'max':         _lua(1)(math_max),
    'min':         _lua(1)(math_min),
    'modf':        _lua(1)(_1(math.modf)),
    'pi':          math.pi,
    'pow':         _lua(1)(_2(math.pow)),
    'rad':         _lua(1)(_1(math.radians)),
    'random':      _lua(1)(math_random),
    'randomseed':  _lua(0)(random.seed),
    'sin':         _lua(1)(_1(math.sin)),
    'sinh':        _lua(1)(_1(math.sinh)),
    'sqrt':        _lua(1)(_1(math.sqrt)),
    'tan':         _lua(1)(_1(math.tan)),
    'tanh':        _lua(1)(_1(math.tanh)),
})
