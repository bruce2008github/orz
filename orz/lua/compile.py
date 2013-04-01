from orz.asm import Opcode, Flag, StringTable
from orz.symbol import Global, Free, Local, Attribute, Name
from orz.visit import Environment as BaseEnvironment, Visitor

from . import ast
from .asm import Assembly, Label
from .runtime.builtins import to_number


class Context(object):
    Load = object()
    Store = object()


class Environment(BaseEnvironment):
    FIELDS = ('asm', 'stringtable', 'break_target', 'context', 'filename')


visit = Visitor()

def set_lineno(func):
    def wrapper(env, node):
        asm = getattr(env, "asm", None)
        if asm is not None:
            asm.set_lineno(node.lineno)

        return func(env, node)

    return wrapper


def visit_function(env, name, node):
    argcount = len(node.args)

    func_name = Name(name)

    asm = Assembly(
        func_name,
        node.symtable.names,
        node.symtable.varnames,
        node.symtable.freevars,
        node.symtable.cellvars,
        argcount = argcount,
        varargs = True,
        parent = env.asm)

    asm.set_lineno(node.lineno)

    func_env = Environment(asm=asm, stringtable=env.stringtable)

    visit_block(func_env, node.body, True)

    for names in (
        node.symtable.names,
        node.symtable.varnames,
        node.symtable.freevars,
        node.symtable.cellvars):

        for name in names:
            name.s = env.stringtable.add(name.name, interned=True)

    func_name.s = env.stringtable.add(func_name.name, interned=True)

    func = env.asm.add_const(asm)

    for i in range(argcount):
        env.asm.load_const(None)

    if not node.symtable.freevars:
        env.asm.emit(Opcode.LOAD_CONST, func)
        env.asm.emit(Opcode.MAKE_FUNCTION, argcount)
    else:
        for freevar in node.symtable.freevars:
            env.asm.emit(Opcode.LOAD_CLOSURE, freevar.parent.slot)

        env.asm.emit(Opcode.BUILD_TUPLE, len(node.symtable.freevars))
        env.asm.emit(Opcode.LOAD_CONST, func)
        env.asm.emit(Opcode.MAKE_CLOSURE, argcount)


def visit_symbol(env, symbol):
    context = {
        Context.Load: 'LOAD_',
        Context.Store: 'STORE_'}[env.context]

    if isinstance(symbol, Local):
        scope = {True: 'DEREF', False: 'FAST'}[symbol.is_referenced]
    else:
        scope = {Global: 'GLOBAL', Free: 'DEREF'}[type(symbol)]

    env.asm.emit(getattr(Opcode, context+scope), symbol.slot)


def visit_exp(env, exp):
    visit(env(context=Context.Load), exp)

    if type(exp) in (ast.ELLIPSIS, ast.Call):
        stacksize = env.asm.stacksize
        # TOS = TOS or (None,)

        label = Label()
        env.asm.emit(Opcode.JUMP_IF_TRUE_OR_POP, label)

        env.asm.load_const(None)
        env.asm.emit(Opcode.BUILD_TUPLE, 1)

        assert stacksize == env.asm.stacksize

        env.asm.emit(Opcode.LABEL, label)

        # TOS = TOS[0]
        env.asm.load_const(0)
        env.asm.emit(Opcode.BINARY_SUBSCR)

        assert stacksize == env.asm.stacksize


def visit_explist(env, explist):
    if not explist:
        env.asm.emit(Opcode.BUILD_TUPLE, 0)
        return

    for subnode in explist[:-1]:
        visit_exp(env, subnode)

    env.asm.emit(Opcode.BUILD_TUPLE, len(explist)-1)

    subnode = explist[-1]

    visit(env(context=Context.Load), subnode)

    if type(subnode) not in (ast.ELLIPSIS, ast.Call):
        env.asm.emit(Opcode.BUILD_TUPLE, 1)

    env.asm.emit(Opcode.BINARY_ADD)


def visit_block(env, stats, return_required=False):
    for subnode in stats:
        visit(env, subnode)
        assert env.asm.stacksize == 0

    if return_required:
        if not stats or not isinstance(stats[-1], ast.Return):
            env.asm.emit(Opcode.BUILD_TUPLE, 0)
            env.asm.emit(Opcode.RETURN_VALUE)


def visit_fields(env, fields):
    env.asm.emit(Opcode.BUILD_MAP, len(fields))

    next = 1

    for field in fields:
        visit(env(context=Context.Load), field)

        if not isinstance(field, ast.Field):
            env.asm.load_const(next)
            next += 1

        env.asm.emit(Opcode.STORE_MAP)

    return next


def is_multi_value(nodes):
    if nodes and type(nodes) in (ast.ELLIPSIS, ast.Call):
        return True

    return False


def prepare_assign(env, need, have, multi_value):
    padding = need - have
    if multi_value:
        padding += 1

    if padding > 0:
        env.asm.load_const(None)
        env.asm.emit(Opcode.BUILD_TUPLE, 1)

        if padding > 1:
            env.asm.load_const(padding)
            env.asm.emit(Opcode.BINARY_MULTIPLY)

        env.asm.emit(Opcode.BINARY_ADD)

    if have > need or multi_value:
        env.asm.load_const(need)
        env.asm.emit(Opcode.SLICE+2)


def to_boolean(env):
    stacksize = env.asm.stacksize

    env.asm.emit(Opcode.DUP_TOP)

    l1, l2, l3 = Label(), Label(), Label()

    # if is None: False
    env.asm.load_const(None)
    env.asm.emit(Opcode.COMPARE_OP, 8)
    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l1)
    assert env.asm.stacksize == stacksize

    env.asm.emit(Opcode.POP_TOP)
    env.asm.load_const(False)

    assert env.asm.stacksize == stacksize
    env.asm.emit(Opcode.JUMP_FORWARD, l3)


    env.asm.emit(Opcode.LABEL, l1)
    # elif is False: False
    env.asm.load_const(False)
    env.asm.emit(Opcode.COMPARE_OP, 8)
    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l2)
    assert env.asm.stacksize == stacksize - 1

    env.asm.load_const(False)

    env.asm.emit(Opcode.JUMP_FORWARD, l3)

    env.asm.stacksize = stacksize - 1
    env.asm.emit(Opcode.LABEL, l2)
    # else: True
    env.asm.load_const(True)
    assert env.asm.stacksize == stacksize

    env.asm.emit(Opcode.LABEL, l3)


@visit.match(ast.Name)
def visit(env, node):
    if not node._env:
        visit_symbol(env, node.symbol)
        return

    # _ENV
    visit_symbol(env(context=Context.Load), node.symbol)

    # node.id
    env.asm.load_const(env.stringtable.add(node.id, interned=True))

    if env.context is Context.Load:
        env.asm.emit(Opcode.BINARY_SUBSCR)

    elif env.context is Context.Store:
        env.asm.emit(Opcode.STORE_SUBSCR)


@visit.match(ast.File)
def visit(env, node):
    file_name = Name('<module>')

    asm = Assembly(
        file_name,
        node.symtable.names,
        node.symtable.varnames,
        node.symtable.freevars,
        node.symtable.cellvars)

    asm.set_lineno(1)

    stringtable = StringTable()

    env = env(asm = asm, stringtable=stringtable)

    visit_block(env, node.body, True)


    for names in (
        node.symtable.names,
        node.symtable.varnames,
        node.symtable.freevars,
        node.symtable.cellvars):

        for name in names:
            name.s = stringtable.add(name.name, interned=True)

    file_name.s = stringtable.add(file_name.name, interned=True)

    stringtable.close()

    return asm


@visit.match(ast.Assign)
def visit(env, node):
    subscript_count = 0

    for subnode in node.target:
        if type(subnode) in (ast.Subscript, ast.Attribute):
            subscript_count += 1

            visit(env(context=None), subnode) # use None to skip STORE_
            env.asm.emit(Opcode.ROT_TWO)

    if subscript_count:
        env.asm.emit(Opcode.BUILD_TUPLE, subscript_count*2)
        env.asm.emit(Opcode.UNPACK_SEQUENCE, subscript_count*2)

    visit_explist(env, node.value)

    prepare_assign(
        env,
        len(node.target),
        len(node.value),
        is_multi_value(node.value))

    env.asm.emit(Opcode.GET_ITER)

    exit_label = Label()

    stacksize = env.asm.stacksize

    for subnode in node.target:
        env.asm.emit(Opcode.FOR_ITER, exit_label)

        if type(subnode) in (ast.Subscript, ast.Attribute):
            env.asm.emit(Opcode.ROT_FOUR)
            env.asm.emit(Opcode.ROT_FOUR)

            env.asm.emit(Opcode.STORE_SUBSCR)
        else:
            visit(env(context=Context.Store), subnode)

    env.asm.emit(Opcode.POP_TOP)
    assert env.asm.stacksize == 0

    env.asm.emit(Opcode.LABEL, exit_label)
    assert env.asm.stacksize == 0


@visit.match(ast.Call)
def visit(env, node):
    visit_exp(env, node.func)

    extra_args = 0
    if isinstance(node.func, ast.Method):
        extra_args = 1

    if not node.args:
        env.asm.emit(Opcode.CALL_FUNCTION, extra_args)
        return

    for subnode in node.args[:-1]:
        visit_exp(env, subnode)

    subnode = node.args[-1]

    visit(env(context=Context.Load), subnode)

    if type(subnode) not in (ast.ELLIPSIS, ast.Call):
        env.asm.emit(
            Opcode.CALL_FUNCTION,
            (extra_args + len(node.args)) & 0xff)
    else:
        env.asm.emit(
            Opcode.CALL_FUNCTION_VAR,
            (extra_args + (len(node.args)-1)) & 0xff )


@visit.match(ast.CallStatement)
def visit(env, node):
    visit(env, node.body)
    env.asm.emit(Opcode.POP_TOP)


@visit.match(ast.Label)
def visit(env, node):
    env.asm.emit(Opcode.LABEL, node.label)


@visit.match(ast.Goto)
def visit(env, node):
    env.asm.emit(Opcode.JUMP_ABSOLUTE, node.label)


@visit.match(ast.Block)
def visit(env, node):
    visit_block(env, node.body)


@visit.match(ast.While)
def visit(env, node):
    l_before, l_after = Label(), Label()

    env.asm.emit(Opcode.LABEL, l_before)

    visit(env, node.test)
    to_boolean(env)
    assert env.asm.stacksize == 1

    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l_after)

    visit_block(env(break_target=l_after), node.body)

    env.asm.emit(Opcode.JUMP_ABSOLUTE, l_before)

    env.asm.emit(Opcode.LABEL, l_after)


@visit.match(ast.Repeat)
def visit(env, node):
    l_before, l_after = Label(), Label()

    env.asm.emit(Opcode.LABEL, l_before)

    visit_block(env(break_target=l_after), node.body)

    visit(env, node.test)
    to_boolean(env)
    assert env.asm.stacksize == 1

    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l_before)

    env.asm.emit(Opcode.LABEL, l_after)


@visit.match(ast.If)
def visit(env, node):
    visit(env, node.test)
    to_boolean(env)

    l_before, l_after = Label(), Label()

    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l_before)
    assert env.asm.stacksize == 0

    visit_block(env, node.body)

    env.asm.emit(Opcode.JUMP_ABSOLUTE, l_after)
    env.asm.emit(Opcode.LABEL, l_before)

    visit_block(env, node.orelse)

    env.asm.emit(Opcode.LABEL, l_after)


@visit.match(ast.For)
def visit(env, node):
    visit_symbol(env(context=Context.Load), node._validate_forloop)
    visit(env(context=Context.Load), node.start)
    visit(env(context=Context.Load), node.stop)
    visit(env(context=Context.Load), node.step)
    env.asm.emit(Opcode.CALL_FUNCTION, 3)
    env.asm.emit(Opcode.UNPACK_SEQUENCE, 3)

    var, limit, step = node._loopvar

    for symbol in node._loopvar:
        visit_symbol(env(context=Context.Store), symbol)

    l_before, l_after = Label(), Label()
    l_smaller, l_body = Label(), Label()

    env.asm.emit(Opcode.LABEL, l_before)

    # if step > 0
    visit_symbol(env(context=Context.Load), step)
    env.asm.load_const(0)
    env.asm.emit(Opcode.COMPARE_OP, 4)
    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l_smaller)

    #   if var > limit
    visit_symbol(env(context=Context.Load), var)
    visit_symbol(env(context=Context.Load), limit)
    env.asm.emit(Opcode.COMPARE_OP, 4)
    #     break
    env.asm.emit(Opcode.POP_JUMP_IF_TRUE, l_after)
    env.asm.emit(Opcode.JUMP_FORWARD, l_body)

    env.asm.emit(Opcode.LABEL, l_smaller)
    # elif step < 0
    visit_symbol(env(context=Context.Load), step)
    env.asm.load_const(0)
    env.asm.emit(Opcode.COMPARE_OP, 0)
    env.asm.emit(Opcode.POP_JUMP_IF_FALSE, l_body)

    #   if var < limit
    visit_symbol(env(context=Context.Load), var)
    visit_symbol(env(context=Context.Load), limit)
    env.asm.emit(Opcode.COMPARE_OP, 0)
    #     break
    env.asm.emit(Opcode.POP_JUMP_IF_TRUE, l_after)

    env.asm.emit(Opcode.LABEL, l_body)
    # local v = var
    visit_symbol(env(context=Context.Load), var)
    visit(env(context=Context.Store), node.target)

    # block
    visit_block(env(break_target=l_after), node.body)

    # var = var + step
    visit_symbol(env(context=Context.Load), var)
    visit_symbol(env(context=Context.Load), step)
    env.asm.emit(Opcode.BINARY_ADD)
    visit_symbol(env(context=Context.Store), var)

    env.asm.emit(Opcode.JUMP_ABSOLUTE, l_before)

    env.asm.emit(Opcode.LABEL, l_after)


@visit.match(ast.ForEach)
def visit(env, node):
    # local f, s, var = explist
    f, s, var = node._loopvar

    visit_explist(env(context=Context.Load), node.iter)
    prepare_assign(env, 3, len(node.iter), True)

    env.asm.emit(Opcode.UNPACK_SEQUENCE, 3)

    for symbol in node._loopvar:
        visit_symbol(env(context=Context.Store), symbol)

    assert env.asm.stacksize == 0

    l_before, l_after = Label(), Label()

    env.asm.emit(Opcode.LABEL, l_before)

    # local var... = f(s,var)
    for symbol in node._loopvar:
        visit_symbol(env(context=Context.Load), symbol)

    env.asm.emit(Opcode.CALL_FUNCTION, 2)

    prepare_assign(env, len(node.target), 1, True)

    env.asm.emit(Opcode.UNPACK_SEQUENCE, len(node.target))

    for subnode in node.target:
        visit(env(context=Context.Store), subnode)

    assert env.asm.stacksize == 0

    # if var_1 == nil then break end
    visit(env(context=Context.Load), node.target[0])

    env.asm.load_const(None)
    env.asm.emit(Opcode.COMPARE_OP, 8)
    env.asm.emit(Opcode.POP_JUMP_IF_TRUE, l_after)

    assert env.asm.stacksize == 0

    # var = var_1
    visit(env(context=Context.Load), node.target[0])
    visit_symbol(env(context=Context.Store), var)

    assert env.asm.stacksize == 0

    # block
    visit_block(env(break_target=l_after), node.body)

    env.asm.emit(Opcode.JUMP_ABSOLUTE, l_before)

    env.asm.emit(Opcode.LABEL, l_after)


@visit.match(ast.Function)
def visit(env, node):
    name = node.name
    if isinstance(name, ast.Attribute):
        name = name.attr
    elif isinstance(name, ast.Method):
        name = name.method

    visit_function(env, name.id, node)
    visit(env(context=Context.Store), node.name)


@visit.match(ast.FunctionLocal)
def visit(env, node):
    visit_function(env, node.name.id, node)
    visit(env(context=Context.Store), node.name)


@visit.match(ast.AssignLocal)
def visit(env, node):
    visit_explist(env, node.value)

    prepare_assign(
        env,
        len(node.target),
        len(node.value),
        is_multi_value(node.value))

    env.asm.emit(Opcode.UNPACK_SEQUENCE, len(node.target))

    for subnode in node.target:
        visit(env(context=Context.Store), subnode)


@visit.match(ast.Return)
def visit(env, node):
    visit_explist(env, node.value)
    env.asm.emit(Opcode.RETURN_VALUE)


@visit.match(ast.Break)
def visit(env, node):
    env.asm.emit(Opcode.JUMP_ABSOLUTE, env.break_target)


@visit.match(ast.Subscript)
def visit(env, node):
    visit(env(context=Context.Load), node.value)
    visit(env(context=Context.Load), node.slice)

    if env.context is Context.Load:
        env.asm.emit(Opcode.BINARY_SUBSCR)
    elif env.context is Context.Store:
        env.asm.emit(Opcode.STORE_SUBSCR)


@visit.match(ast.Attribute)
def visit(env, node):
    visit(env(context=Context.Load), node.value)

    env.asm.set_lineno(node.attr.lineno)
    env.asm.load_const(env.stringtable.add(node.attr.id, interned=True))

    if env.context is Context.Load:
        env.asm.emit(Opcode.BINARY_SUBSCR)
    elif env.context is Context.Store:
        env.asm.emit(Opcode.STORE_SUBSCR)


@visit.match(ast.Method)
def visit(env, node):
    visit(env(context=Context.Load), node.value)

    if env.context is Context.Load:
        env.asm.emit(Opcode.DUP_TOP)

    env.asm.set_lineno(node.method.lineno)
    env.asm.load_const(env.stringtable.add(node.method.id, interned=True))

    if env.context is Context.Load:
        env.asm.emit(Opcode.BINARY_SUBSCR)
        env.asm.emit(Opcode.ROT_TWO)
    elif env.context is Context.Store:
        env.asm.emit(Opcode.STORE_SUBSCR)


@visit.match(ast.NIL)
def visit(env, node):
    env.asm.load_const(None)


@visit.match(ast.FALSE)
def visit(env, node):
    env.asm.load_const(False)


@visit.match(ast.TRUE)
def visit(env, node):
    env.asm.load_const(True)


@visit.match(ast.Number)
def visit(env, node):
    env.asm.load_const(to_number(node.n.lower()))


@visit.match(ast.String)
def visit(env, node):
    env.asm.load_const(env.stringtable.add(node.s))


@visit.match(ast.ELLIPSIS)
def visit(env, node):
    visit_symbol(env, node.symbol)


@visit.match(ast.Field)
def visit(env, node):
    visit_exp(env, node.key)
    visit_exp(env, node.value)
    env.asm.emit(Opcode.ROT_TWO)


@visit.match(ast.Table)
def visit(env, node):
    visit_symbol(env(context=Context.Load), node._luatable)

    if not node.fields or type(node.fields[-1]) not in (ast.Call, ast.ELLIPSIS):
        next = visit_fields(env, node.fields)
        env.asm.load_const(next)
        env.asm.emit(Opcode.CALL_FUNCTION, 2)
        return

    next = visit_fields(env, node.fields[:-1])

    env.asm.load_const(next)

    visit(env(context=Context.Load), node.fields[-1])

    env.asm.emit(Opcode.GET_ITER)

    l_before, l_after = Label(), Label()

    env.asm.emit(Opcode.LABEL, l_before)

    stacksize = env.asm.stacksize

    env.asm.emit(Opcode.FOR_ITER, l_after)

    env.asm.emit(Opcode.ROT_THREE)
    env.asm.emit(Opcode.ROT_FOUR)
    env.asm.emit(Opcode.DUP_TOP)
    env.asm.emit(Opcode.ROT_FOUR)
    env.asm.emit(Opcode.STORE_MAP)
    env.asm.emit(Opcode.ROT_THREE)
    env.asm.load_const(1)
    env.asm.emit(Opcode.BINARY_ADD)
    env.asm.emit(Opcode.ROT_TWO)

    env.asm.emit(Opcode.JUMP_ABSOLUTE, l_before)
    assert env.asm.stacksize == stacksize

    env.asm.stacksize -= 1
    env.asm.emit(Opcode.LABEL, l_after)

    env.asm.emit(Opcode.CALL_FUNCTION, 2)


@visit.match(ast.Lambda)
def visit(env, node):
    visit_function(env, '<lambda>', node)


@visit.match(ast.BinOp)
def visit(env, node):
    visit_symbol(env(context=Context.Load), node._op)
    visit(env(context=Context.Load), node.left)
    visit(env(context=Context.Load), node.right)
    env.asm.emit(Opcode.CALL_FUNCTION, 2)


@visit.match(ast.UnaryOp)
def visit(env, node):
    visit_symbol(env(context=Context.Load), node._op)
    visit(env(context=Context.Load), node.operand)
    env.asm.emit(Opcode.CALL_FUNCTION, 1)


visit = set_lineno(visit)
