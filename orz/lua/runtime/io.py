from __future__ import absolute_import

import os
import sys
import tempfile
from functools import wraps

from .builtins import LuaTable, _lua, to_string, to_number


def catch_io_error(func):
    @wraps(func)
    def wrapper(*args):
        try:
            return func(*args)
        except IOError as e:
            return None, e.strerror, float(e.errno)

    return wrapper


def file_close(f):
    f._file.close()
    return True


def file_flush(f):
    f._file.flush()
    return True


def _read(f, arg):
    if arg == '*a':
        return f.read()
    elif arg == '*l':
        line = f.readline()
        if line == '':
            return None
        return line.rstrip('\n')
    elif arg == '*L':
        return f.readline() or None

    arg = int(to_number(arg))
    if arg == 0:
        return ''

    return f.read(arg) or None


def file_read(f, *args):
    args = args or ("*l",)
    return tuple(_read(f._file, arg) for arg in args)


def file_seek(f, whence="cur", offset=0.0):
    whence = to_string(whence)
    offset = int(to_number(offset))

    whence = {
        "set": os.SEEK_SET,
        "cur": os.SEEK_CUR,
        "end": os.SEEK_END }[whence]

    f._file.seek(offset, whence)
    return f._file.tell()


def file_write(f, *args):
    for a in args:
        f._file.write(to_string(a))

    return f


_file_metatable = LuaTable({
    'close':  _lua(1)(file_close),
    'flush':  _lua(1)(file_flush),
    'read':   file_read,
    'seek':   catch_io_error(_lua(1)(file_seek)),
    'write':  catch_io_error(_lua(1)(file_write)),
    })


def io_close(f=None):
    if f is None:
        f = _default_output
    return _file_metatable["close"](f)


def io_flush():
    return _file_metatable["flush"](_default_output)


def io_input(f=None):
    if f is not None:
        if isinstance(f, LuaTable):
            _default_input = f._file
        else:
            f = to_string(f)
            _default_input = io_open(f, 'r')

    return _default_input


def io_open(filename, mode='r'):
    filename = to_string(filename)
    mode = to_string(mode)

    f = LuaTable()
    f._file = open(filename, mode)
    return f


def io_output(f=None):
    if f is not None:
        if isinstance(f, LuaTable):
            _default_output = f._file
        else:
            f = to_string(f)
            _default_output = io_open(f, 'w')

    return _default_output


def io_read(*args):
    return _file_metatable["read"](_default_input, *args)


def io_tmpfile():
    fd, filename = tempfile.mkstemp()
    f = LuaTable()
    f._file = os.fdopen(fd)
    return f


def io_type(obj):
    if not isinstance(obj, LuaTable):
        return

    f = getattr(obj, '_file', None)
    if f is None:
        return

    if f._file.closed:
        return "closed file"

    return "file"


def io_write(*args):
    return _file_metatable["write"](_default_output, *args)


io_stdin = LuaTable()
io_stdin._metatable = _file_metatable
io_stdin._file = sys.stdin

io_stdout = LuaTable()
io_stdout._metatable = _file_metatable
io_stdout._file = sys.stdout

io_stderr = LuaTable()
io_stderr._metatable = _file_metatable
io_stderr._file = sys.stderr

_default_input = io_stdin
_default_output = io_stdout


mod_io = LuaTable({
    'stdin':    io_stdin,
    'stdout':   io_stdout,
    'stderr':   io_stderr,

    'close':    io_close,
    'flush':    io_flush,
    'input':    _lua(1)(io_input),
    'open':     catch_io_error(_lua(1)(io_open)),
    'output':   _lua(1)(io_output),
    'read':     io_read,
    'tmpfile':  _lua(1)(io_tmpfile),
    'type':     _lua(1)(io_type),
    'write':    io_write,
})
