from __future__ import absolute_import

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import marshal


from .. import parse, scope, label, compile
from .builtins import LuaTable, BUILTINS, mod_builtin, _lua, to_string
from .string import mod_string
from .math import mod_math
from .table import mod_table
from .os import mod_os
from .io import mod_io


def compile_lua(code, filename='<string>'):
    parser = parse.Parser(filename=filename)

    ast = parser.parse(code)
    ast = scope.visit(scope.Environment(filename=filename), ast)
    ast = label.visit(label.Environment(filename=filename), ast)
    asm = compile.visit(compile.Environment(filename=filename), ast)

    buf = StringIO.StringIO()
    asm.serialize(buf, filename)

    return buf.getvalue()


_loaded = LuaTable({
    'string':        mod_string,
    'math':          mod_math,
    "table":         mod_table,
    "io":            mod_io,
    "os":            mod_os,
})


def require(modname):
    modname = to_string(modname)
    mod = _loaded.data.get(modname, None)

    if mod is not None:
        return mod

    mod = loadfile(modname+'.lua')()[0]

    _loaded.data[modname] = mod

    return mod


def load(ld, filename="<string>", mode='t', env=None):
    if env is None:
        env = _ENV

    if mode == 't':
        filename = to_string(filename)
        ld = compile_lua(ld, filename)

    code = marshal.loads(ld)
    return lambda: eval(
        code,
        { "__builtins__":   BUILTINS,
          "_ENV":           env})


def loadfile(filename, mode='t', env=None):
    filename = to_string(filename)

    with open(filename, 'r') as f:
        ld = f.read()

    return load(ld, filename, mode, env)


_G = LuaTable({
    'require':       _lua(1)(require),
    'load':          _lua(1)(load),
    'loadfile':      _lua(1)(loadfile),

    'string':        require("string"),
    'math':          require("math"),
    "table":         require("table"),
    "io":            require("io"),
    "os":            require("os"),

    '_VERSION':      "Lua 5.2",
})


_G.data.update(mod_builtin.data)

_ENV = _G.copy()
