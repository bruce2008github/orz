from __future__ import absolute_import

import re

from .builtins import LuaTable, _lua, to_number, to_string


def string_byte(s, i=1.0, j=1.0):
    s = to_string(s)
    i = to_number(i)
    j = to_number(j)

    return map(_slice(s, i, j))


def string_char(*args):
    return ''.join(map(chr, args))


def string_format(format, *args):
    return to_string(format)%args


def string_gmatch(s, pattern):
    it = re.finditer(to_string(pattern), to_string(s))

    @_lua(1)
    def f(s, var):
        try:
            return it.next().group(0)
        except StopIteration:
            return

    return f, None, None


def string_gsub(s, pattern, repl, n=None):
    s = to_string(s)
    pattern = to_string(pattern)

    if n is not None:
        n = to_number(n)
        n = int(n)

        if n == 0:
            return s, 0.0

    if isinstance(repl, str):
        replace = repl

    elif isinstance(repl, LuaTable):
        def replace(match):
            return repl[match.group(1)]

    else:
        def replace(match):
            groups = match.groups() or (match.group(0),)
            return repl(*groups)

    s, n = re.subn(pattern, replace, s, n or 0)
    return s, float(n)


def string_len(s):
    return len(to_string(s))


def string_lower(s):
    return to_string(s).lower()


def string_match(s, pattern, i=1.0):
    s = to_string(s)
    pattern = to_string(pattern)
    i = int(to_number(i))

    l = len(s)

    i += l+1 if i<0 else 0
    i = i or 1

    s = s[i:]

    match = re.match(pattern, s)
    if match is None:
        return

    return match.group(0)


def string_rep(s, n, sep=None):
    s = to_string(s)
    n = int(to_number(n))

    if sep is None:
        return s*n

    return to_string(sep).join(s for i in xrange(n))


def string_reverse(s):
    return to_string(s)[::-1]


def string_sub(s, i, j=-1):
    return _slice(
        to_string(s),
        to_number(i),
        to_number(j))


def string_upper(s):
    return to_string(s).upper()


mod_string = LuaTable({
    'byte':     _lua()(string_byte),
    'char':     _lua(1)(string_char),
    'format':   _lua(1)(string_format),
    'gmatch':   string_gmatch,
    'gsub':     string_gsub,
    'len':      _lua(1)(string_len),
    'lower':    _lua(1)(string_lower),
    'match':    _lua(1)(string_match),
    'rep':      _lua(1)(string_rep),
    'reverse':  _lua(1)(string_reverse),
    'sub':      _lua(1)(string_sub),
    'upper':    _lua(1)(string_upper),
})
