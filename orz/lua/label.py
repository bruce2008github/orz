from orz.ast import NodeListField
from orz.visit import Environment as BaseEnvironment, Visitor

from . import ast
from .asm import Label


class LabelTable(object):


    def __init__(self):
        self.labels = {}
        self.gotos = {} # pending goto
        self.locals = []


    def close(self, is_last=False):
        remain = self.gotos.keys()
        if not is_last:
            return remain

        # TODO: sort by lexpos
        if remain:
            raise SyntaxError("no visible label '{}' for <goto> at line {:d}")


    def declare_locals(self, locals):
        self.locals.extend(locals)


    def got_label(self, label):
        label.label = Label()
        name = label.name

        other = self.labels.get(name, None)

        if other is not None:
            # TODO: ,(filename, lineno, offset, text)
            raise SyntaxError(
                "label '{}' already defined on line {:d}".format(
                    name, other.lineno))

        self.labels[name] = label

        resolved = [ goto for goto in self.gotos if goto.target == name ]

        for goto in resolved:
            goto.label = label.label
            nlocals = self.gotos.pop(goto)

            if nlocals < len(self.locals): # XXX
                raise SyntaxError(
                    "<goto {}> at line {:d} jumps into the scope of local '{}'".format(
                        name, goto.lineno, self.locals[nlocals]))


    def got_goto(self, goto):
        label = self.labels.get(goto.target, None)
        if label is None:
            self.gotos[goto] = len(self.locals)
        else:
            goto.label = label.label



class Environment(BaseEnvironment):
    FIELDS = ('filename', 'label_table')



visit = Visitor()



def nop(env, node):
    pass


def visit_topblock(env, node):
    label_table = LabelTable()

    for subnode in node.body:
        visit(env(label_table=label_table), subnode)

    label_table.close(True)
    return node


def visit_subblock(env, nodes):
    block_table = LabelTable()

    for node in nodes:
        visit(env(label_table=block_table), node)

    for goto in block_table.close():
        env.label_table.got_goto(goto)


def visit_body(env, node):
    visit_subblock(env, node.body)


@visit.match(ast.Label)
def visit_Label(env, node):
    env.label_table.got_label(node)


@visit.match(ast.Goto)
def visit_Goto(env, node):
    env.label_table.got_goto(node)


visit.match(ast.Block)(visit_body)
visit.match(ast.While)(visit_body)
visit.match(ast.Repeat)(visit_body)
visit.match(ast.For)(visit_body)
visit.match(ast.ForEach)(visit_body)


@visit.match(ast.If)
def visit_If(env, node):
    visit_subblock(env, node.body)
    visit_subblock(env, node.orelse)


visit.match(ast.File)(visit_topblock)
visit.match(ast.Function)(visit_topblock)


@visit.match(ast.FunctionLocal)
def visit_FunctionLocal(env, node):
    visit_topblock(env, node)
    env.label_table.declare_locals([node.name.id])


@visit.match(ast.AssignLocal)
def visit_AssignLocal(env, node):
    env.label_table.declare_locals([t.id for t in node.target])


visit.match(ast.Assign)(nop)
visit.match(ast.CallStatement)(nop)
visit.match(ast.Return)(nop)
visit.match(ast.Break)(nop)
