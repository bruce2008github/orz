from __future__ import absolute_import

from .builtins import LuaTable, _lua, lt_event, _slice, to_string, to_number


def table_concat(table, sep="", i=1.0, j=-1.0):
    return "".join(map(
            to_string,
            _slice(
                table.list,
                to_number(i),
                to_number(j))))


def table_insert(table, value, pos=None):
    length = len(table)

    if pos is not None:
        pos, value = value, int(to_number(pos)) - 1
    else:
        pos = length

    table.list.insert(pos, value)


def table_pack(*args):
    table = LuaTable()
    table.list = list(args)
    table.data["n"] = len(args)
    return table


def table_remove(table, pos=None):
    if pos is None:
        pos = len(table) - 1
    else:
        pos = int(to_number(pos)) - 1

    if 0<= pos < len(table):
        table.list.pop(pos)


def table_sort(table, comp=None):
    if comp is None:
        table.list.sort(cmp=lt_event)

    def wrapper(op1, op2):
        return comp(op1, op2)[0]

    table.list.sort(wrapper)


def table_unpack(table, i=1.0, j=-1.0):
    return _slice(
        table.list,
        to_number(i),
        to_number(j))


mod_table = LuaTable({
    'concat':  _lua(1)(table_concat),
    'insert':  _lua(0)(table_insert),
    'pack':    _lua(1)(table_pack),
    'remove':  _lua(0)(table_remove),
    'sort':    _lua(0)(table_sort),
    'unpack':  _lua()(table_unpack),
})
