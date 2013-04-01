from __future__ import absolute_import

from functools import wraps
import math
import operator
import re
import sys
import types



def _float_to_int(f):
    if not isinstance(f, float):
        return

    i = int(f)
    if i == f:
        return i


def to_string(s):
    if isinstance(s, str):
        return s

    if isinstance(s, float):
        return '{:.14g}'.format(s)

    raise TypeError("string expected")


def to_number(s):
    n = tonumber(s)

    if n is None:
        raise TypeError("number expected")

    return n


def _slice(s,i,j):
    i, j = int(i), int(j)
    l = len(s)

    i += l+1 if i<0 else 0
    j += l+1 if j<0 else 0

    i = i or 1
    j = l if j > l else j

    return s[i-1:j]



class LuaTable(object):


    def __init__(self, data=None, hint=1):
        data = data or {}

        self.list = [data.pop(i) for i in xrange(1, hint)]
        self._strip_list()

        self.data = data
        self._propagate_list()


    def _strip_list(self):
        while self.list and self.list[-1] is None:
            self.list.pop()


    def _propagate_list(self):
        while True:
            i = len(self.list)+1

            value = self.data.pop(i, None)

            if value is None:
                break

            self.list.append(i)


    def copy(self):
        return LuaTable(self.data.copy())


    def __len__(self):
        return len(self.list)


    def __getitem__(self, name):
        i = _float_to_int(name)
        if i is not None:
            if 1 <= i <= len(self.list):
                return self.list[i-1]

        value = self.data.get(name, None)

        if value is not None:
            return value

        h = get_event_handler(self, "__index")

        if h is None:
            return

        if isinstance(h, LuaTable): # XXX
            return h[name]

        return h(name)


    def __setitem__(self, name, value):
        i = _float_to_int(name)
        if i is not None:
            length = len(self.list)

            if 1 <= i <= length:
                self.list[i-1] = value

                if i != length or value is not None:
                    return

                self._strip_list()

            elif i == length + 1:
                self.list.append(value)
                self._propagate_list()


        if name in self.data:
            if value is None:
                del self.data[name]
            else:
                self.data[name] = value

            return

        h = get_event_handler(self, "__newindex")

        if h is None:
            self.data[name] = value
            return

        if isinstance(h, LuaTable):
            h[name] = value
            return

        h(table, name, value)


    def __call__(self, *args):
        h = get_event_handler(self, "__call")
        if h is not None:
            return h(self, *args)

        raise Exception("attempt to call a table value")


    def rawget(self, index):
        return self.data.get(index, None)


    def rawset(self, index, value):
        self.data.set(index, value)
        return self


    def getmetatable(self):
        mt = getattr(self, '_metatable', None)
        if mt is None:
            return

        protected = mt['__metatable']
        if protected is not None:
            return protected

        return mt


    def setmetatable(self, metatable):
        mt = getattr(self, '_metatable', None) or {}

        if mt is not None:
            if mt['__metatable'] is not None:
                raise Exception("cannot change a protected metatable")

        if metatable is None:
            if mt is not None:
                delattr(self, '_metatable')
        else:
            self.__metatable = metatable

        return self


def _assert(v, message="assertion failed"):
    assert is_true(v), message
    return v


def error(message, level=None):
    raise Exception(message)


def _ipairs(t, n):
    n += 1
    v = t[n]

    if v is not None:
        return n, v
    else:
        return None, v


def ipairs(t):
    h = get_event_handler(t, "__ipairs")

    if h is not None:
        return h(t)

    return _ipairs, t, 0.0


def rawequal(v1, v2):
    return (v1 is v2)


def rawget(table, index):
    if not isinstance(table, LuaTable):
        raise TypeError("table expected")

    return table.rawget(index)


def rawset(table, index, value):
    if not isinstance(table, LuaTable):
        raise TypeError("table expected")

    if index is None:
        raise TypeError("table index is nil")

    return table.rawset(index, value)


def rawlen(v):
    return len(v)


def getmetatable(table):
    if isinstance(table, LuaTable):
        return table.getmetatable()


def setmetatable(table, metatable):
    if not isinstance(table, LuaTable):
        raise TypeError("table expected")

    return table.setmetatable(metatable)


def select(index, *args):
    if index == '#':
        return len(args),

    index = int(tonumber(index))

    if index == 0:
        raise IndexError("index out of range")

    if index > 0:
        index -= 1

    return args[index:]


NUMBER_RE = re.compile(
    r'0x(?:[0-9a-f]+(?:\.[0-9a-f]+)?|\.[0-9a-f]+)(?:p[+-]?\d+)?|(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?')

MANT_DIG = sys.float_info.mant_dig


def _tonumber(e):
    if not e.startswith('0x'):
        return float(e)

    base, _, exp = e[2:].partition('p')
    base, _, frac = base.partition('.')

    if not exp and not frac:
        return int(base, 16)

    base += frac
    l = len(base)
    base = base.rstrip('0')
    l -= len(base)

    base = int(base, 16)
    exp = int(exp or '0') - len(frac) * 4 + l * 4

    bits = base.bit_length() - MANT_DIG

    if bits > 0:
        # XXX
        base >>= bits - 1
        if base & 1:
            base += 1
        base >>= 1

        exp += bits

    return float(base)*2.0**exp # XXX: overflow


def tonumber(e, base=None):
    if isinstance(e, float):
        return e

    if not isinstance(e, str):
        return

    e = e.strip().lower()

    try:
        if base is not None:
            return int(e, base)

        if NUMBER_RE.match(e):
            return _tonumber(e)

    except Exception:
        return


def tostring(v):
    formatter = {
        types.NoneType: lambda _: 'nil',
        bool: lambda v: {True: 'true', False: 'false'}[v],
        str: lambda v: v,
        float: '{:.14g}'.format}.get(type(v), None)

    if formatter is not None:
        return formatter(v)

    if isinstance(v, LuaTable):
        mt = v.getmetatable()
        if mt is not None:
            _tostring = mt["__tostring"]

            if _tostring is not None:
                return _tostring(v)

        return 'table: '+ hex(id(v))

    elif isinstance(v, types.FunctionType):
        return 'function: ' + hex(id(v))

    else:
        raise NotImplementedError()


def validate_forloop(initial, limit, step):
    initial = tonumber(initial)

    if initial is None:
        raise TypeError("'for' initial value must be a number")

    limit = tonumber(limit)

    if limit is None:
        raise TypeError("'for' limit value must be a number")

    step = tonumber(step)

    if step is None:
        raise TypeError("'for' step value must be a number")

    return initial, limit, step


def get_event_handler(o, event):
    return (getmetatable(o) or LuaTable()).rawget(event)


def getbinhandler(op1, op2, event):
    return get_event_handler(op1, event) or get_event_handler(op2, event)


def binop(event, op):

    def handler(op1, op2):
        o1, o2 = tonumber(op1), tonumber(op2)

        if o1 is not None and o2 is not None:
            try:
                return op(o1, o2)
            except OverflowError:
                return float("inf")

        h = getbinhandler(op1, op2, "__"+event)

        if h is not None:
            return h(op1, op2)

        raise TypeError("attempt to perform arithmetic on non-number value")

    handler.__name__ = event + '_event'

    return handler


def concat_event(op1, op2):
    o1, o2 = op1, op2

    if isinstance(o1, float):
        o1 = tostring(o1)

    if isinstance(o1, float):
        o2 = tostring(o2)

    if isinstance(o1, str) and isinstance(o2, str):
        return o1 + o2

    h = getbinhandler(op1, op2, "__concat")

    if h is not None:
        return h(op1, op2)

    raise TypeError("attempt to concatenate non-string value")


def unm_event(op):
    o = tonumber(op)

    if o is not None:
        return -o

    h = get_event_handler(o, "__unm")

    if h is not None:
        return h(o)

    raise TypeError("attempt to perform arithmetic on non-number value")


def len_event(op):
    if isinstance(op, str):
        return len(op)

    h = get_event_handler(op, "__len")

    if h is not None:
        return h(op)

    elif isinstance(op, LuaTable):
        return len(op)

    raise TypeError("attempt to get length")


def lt_event(op1, op2):
    if isinstance(op1, float) and isinstance(op2, float):
        return op1 < op2

    elif isinstance(op1, str) and isinstance(op2, str):
        return op1 < op2

    h = getbinhandler(op1, op2, "__lt")

    if h is not None:
        return not_event(not_event(h(op1, op2)))

    raise TypeError("attempt to compare")


def le_event(op1, op2):
    if isinstance(op1, float) and isinstance(op2, float):
        return op1 <= op2

    elif isinstance(op1, str) and isinstance(op2, str):
        return op1 <= op2

    h = getbinhandler(op1, op2, "__le")
    if h is not None:
        return not_event(not_event(h(op1, op2)))

    h = getbinhandler(op1, op2, "__lt")
    if h is not None:
        return not_event(h(op2, op1))

    raise TypeError("attempt to compare")


def gt_event(op1, op2):
    return lt_event(op2, op1)


def ge_event(op1, op2):
    return le_event(op2, op1)


def getequalhandler(op1, op2):
    if type(op1) != type(op2):
        return

    if not isinstance(op1, LuaTable):
        return

    mm1 = get_event_handler(op1, "__eq")
    mm2 = get_event_handler(op1, "__eq")

    if mm1 == mm2:
        return mm1


def eq_event(op1, op2):
    if op1 == op2:
        return True

    h = getequalhandler(op1, op2)
    if h is not None:
        return not_event(not_event(h(op1, op2)))

    return False


def ne_event(op1, op2):
    return not eq_event(op1, op2)


def is_true(o):
    return o is not False and o is not None


def and_event(op1, op2):
    if is_true(op1):
        return op2

    return op1


def or_event(op1, op2):
    if is_true(op1):
        return op1

    return op2


def not_event(op):
    return not is_true(op)


def _luadiv(o1, o2):
    if o2 == 0.0:
        if o1 == 0.0:
            return float("nan")
        return float("inf")

    return operator.truediv(o1, o2)


BUILTINS = {
    'validate_forloop': validate_forloop,
    'LuaTable': LuaTable,

    '.b+':   binop("add", operator.add),
    '.b-':   binop("sub", operator.sub),
    '.b*':   binop("mul", operator.mul),
    '.b/':   binop("div", _luadiv),
    '.b%':   binop("mod", operator.mod),
    '.b^':   binop("pow", operator.pow),
    '.band': and_event,
    '.bor':  or_event,
    '.b..':  concat_event,

    '.b<':   lt_event,
    '.b<=':  le_event,
    '.b>':   gt_event,
    '.b>=':  ge_event,
    '.b==':  eq_event,
    '.b~=':  ne_event,

    '.u-':   unm_event,
    '.u#':   len_event,
    '.unot': not_event,
}


def _lua(ret=None):
    convert_result = {
        None:   lambda _: tuple(_),
        1:      lambda _: (_,),
        0:      lambda _: (),
        }[ret]

    def decorator(func):
        @wraps(func)
        def wrapper(*args):
            return convert_result(func(*args))

        return wrapper

    return decorator


def _print(*args):
    for arg in args:
        arg = tostring(arg)
        sys.stdout.write(arg)
        sys.stdout.write('\t')

    print


mod_builtin = LuaTable({
    'assert':        _lua(1)(_assert),
    'error':         _lua(1)(error),
    'getmetatable':  _lua(1)(getmetatable),
    'ipairs':        ipairs,
    'print':         _lua(0)(_print),
    'rawequal':      _lua(1)(rawequal),
    'rawget':        _lua(1)(rawget),
    'rawlen':        _lua(1)(rawlen),
    'rawset':        _lua(1)(rawset),
    'select':        select,
    'setmetatable':  _lua(1)(setmetatable),
    'tonumber':      _lua(1)(tonumber),
    'tostring':      _lua(1)(tostring),
})
