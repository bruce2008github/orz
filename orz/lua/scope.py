from orz.ast import NodeListField
from orz.symbol import Global, Free, Local, Attribute, calculate_slots
from orz.visit import Environment as BaseEnvironment, Visitor

from . import ast



class BaseSymbolTable(object):


    def __init__(self, parent):
        self.parent = parent
        self.table = {}


    def get_attribute(self, name):
        return self.add_symbol(Attribute(name))


    def get_global(self, name):
        return self.add_symbol(Global(name))


    def add_local(self, name):
        return self.add_symbol(Local(name))


    def declare_local(self, name):
        symbol = self.add_local(name)
        self.table[name] = symbol
        return symbol


    def find(self, name):
        symbol = self.table.get(name, None)
        if symbol:
            return symbol

        if self.parent is not None:
            symbol = self.parent.find(name)

            if symbol is not None:
                return self._found(name, symbol)



class SymbolTable(BaseSymbolTable):


    def __init__(self, parent=None):
        super(SymbolTable, self).__init__(parent)
        self.symbols = []

        self._loopvars = []


    def close(self):
        self.names, self.varnames, self.freevars, self.cellvars = calculate_slots(self.symbols)


    def get_loopvar(self, n=0):
        if n >= len(self._loopvars):
            loopvar = (
                self.add_local(".{:d}a".format(n)),
                self.add_local(".{:d}b".format(n)),
                self.add_local(".{:d}c".format(n)))

            self._loopvars.append(loopvar)

        return self._loopvars[n]


    def add_symbol(self, symbol):
        self.symbols.append(symbol)
        return symbol


    def _found(self, name, symbol):
        if isinstance(symbol, Global):
            symbol = self.get_global(symbol.name)
        else:
            if isinstance(symbol, Local):
                symbol.is_referenced = True

            symbol = self.add_symbol(Free(name, symbol))

        self.table[name] = symbol
        return symbol



class BlockSymbolTable(BaseSymbolTable):


    def get_loopvar(self, n=0):
        return self.parent.get_loopvar(n)


    def add_symbol(self, symbol):
        return self.parent.add_symbol(symbol)


    def _found(self, name, symbol):
        self.table[name] = symbol
        return symbol



class ForLoopBlockSymbolTable(BlockSymbolTable):


    def get_loopvar(self, n=0):
        return self.parent.get_loopvar(n+1)



class Environment(BaseEnvironment):
    FIELDS = ('filename', 'symtable')



visit = Visitor()



def nop(env, node):
    pass



def default(env, node):
    for field in node._node_fields:
        if isinstance(getattr(node.__class__, field), NodeListField):
            for subnode in getattr(node, field):
                visit(env, subnode)
        else:
            visit(env, getattr(node, field))


def visit_function(env, node):
    symtable = SymbolTable(env.symtable)

    for arg in node.args:
        symtable.declare_local(arg.id)

    if node.varargs:
        symtable.declare_local('...')
    else:
        symtable.declare_local('__...__')

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)

    symtable.close()
    node.symtable = symtable



@visit.match(ast.Name)
def visit(env, node):
    node._env = False
    symbol = env.symtable.find(node.id)

    if symbol is None:
        node._env = True
        symbol = env.symtable.find("_ENV")

    node.symbol = symbol


@visit.match(ast.File)
def visit(env, node):
    symtable = SymbolTable()
    symtable.table["_ENV"] = symtable.get_global("_ENV")

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)

    symtable.close()
    node.symtable = symtable
    return node


@visit.match(ast.Block)
def visit(env, node):
    symtable = BlockSymbolTable(env.symtable)

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)


@visit.match(ast.While)
def visit(env, node):
    visit(env, node.test)

    symtable = BlockSymbolTable(env.symtable)

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)


@visit.match(ast.Repeat)
def visit(env, node):
    symtable = BlockSymbolTable(env.symtable)

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)

    visit(env(symtable=symtable), node.test)


@visit.match(ast.If)
def visit(env, node):
    visit(env, node.test)

    symtable1 = BlockSymbolTable(env.symtable)

    for subnode in node.body:
        visit(env(symtable=symtable1), subnode)

    symtable2 = BlockSymbolTable(env.symtable)

    for subnode in node.orelse:
        visit(env(symtable=symtable2), subnode)


@visit.match(ast.For)
def visit(env, node):
    node._validate_forloop = env.symtable.get_global("validate_forloop")

    visit(env.symtable, node.start)
    visit(env.symtable, node.stop)
    visit(env.symtable, node.step)

    node._loopvar = env.symtable.get_loopvar()

    symtable = ForLoopBlockSymbolTable(env.symtable)

    symtable.declare_local(node.target.id)
    visit(env(symtable=symtable), node.target)

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)


@visit.match(ast.ForEach)
def visit(env, node):
    for subnode in node.iter:
        visit(env, subnode)

    node._loopvar = env.symtable.get_loopvar()

    symtable = ForLoopBlockSymbolTable(env.symtable)

    for subnode in node.target:
        symtable.declare_local(subnode.id)

    for subnode in node.target:
        visit(env(symtable=symtable), subnode)

    for subnode in node.body:
        visit(env(symtable=symtable), subnode)


@visit.match(ast.Function)
def visit(env, node):
    visit(env, node.name)

    visit_function(env, node)


@visit.match(ast.FunctionLocal)
def visit(env, node):
    env.symtable.declare_local(node.name.id)
    visit(env, node.name)

    visit_function(env, node)


@visit.match(ast.AssignLocal)
def visit(env, node):
    for subnode in node.value:
        visit(env, subnode)

    for subnode in node.target:
        env.symtable.declare_local(subnode.id)

    for subnode in node.target:
        visit(env, subnode)


@visit.match(ast.ELLIPSIS)
def visit(env, node):
    symbol = env.symtable.find('...')
    assert symbol is not None # TODO proper error message
    node.symbol = symbol


@visit.match(ast.BinOp)
def visit(env, node):
    node._op = env.symtable.get_global(".b"+node.op)
    visit(env, node.left)
    visit(env, node.right)


@visit.match(ast.UnaryOp)
def visit(env, node):
    node._op = env.symtable.get_global(".u"+node.op)
    visit(env, node.operand)


@visit.match(ast.Lambda)
def visit(env, node):
    visit_function(env, node)


@visit.match(ast.Table)
def visit(env, node):
    node._luatable = env.symtable.get_global("LuaTable")

    for subnode in node.fields:
        visit(env, subnode)


visit.match(ast.Label)(nop)
visit.match(ast.Goto)(nop)
visit.match(ast.Assign)(default)
visit.match(ast.CallStatement)(default)
visit.match(ast.Call)(default)
visit.match(ast.Return)(default)
visit.match(ast.Break)(nop)
visit.match(ast.Subscript)(default)
visit.match(ast.Attribute)(default)
visit.match(ast.Method)(default)
visit.match(ast.NIL)(nop)
visit.match(ast.FALSE)(nop)
visit.match(ast.TRUE)(nop)
visit.match(ast.Number)(nop)
visit.match(ast.String)(nop)
visit.match(ast.Field)(default)
