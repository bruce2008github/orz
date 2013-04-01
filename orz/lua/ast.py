from orz.ast import Node, NodeField, NodeListField, ValueField


class StatementNode(Node):
    pass

class ExpressionNode(Node):
    pass

class VarNode(ExpressionNode):
    pass

class FuncNameNode(VarNode):
    pass

class BinOpNode(Node):
    pass

class UnaryOpNode(Node):
    pass

class Name(FuncNameNode):
    id = ValueField(str)

class File(Node):
    body = NodeListField(StatementNode)

class Assign(StatementNode):
    value = NodeListField(ExpressionNode)
    target = NodeListField(VarNode)

class Call(ExpressionNode):
    func = NodeField(ExpressionNode)
    args = NodeListField(ExpressionNode)

class CallStatement(StatementNode):
    body = NodeField(Call)

class Label(StatementNode):
    name = ValueField(str)

class Goto(StatementNode):
    target = ValueField(str)

class Block(StatementNode):
    body = NodeListField(StatementNode)

class While(StatementNode):
    test = NodeField(ExpressionNode)
    body = NodeListField(StatementNode)

class Repeat(StatementNode):
    body = NodeListField(StatementNode)
    test = NodeField(ExpressionNode)

class If(StatementNode):
    test = NodeField(ExpressionNode)
    body = NodeListField(StatementNode)
    orelse = NodeListField(StatementNode)

class For(StatementNode):
    start = NodeField(ExpressionNode)
    stop = NodeField(ExpressionNode)
    step = NodeField(ExpressionNode)
    target = NodeField(Name)
    body = NodeListField(StatementNode)

class ForEach(StatementNode):
    iter = NodeListField(ExpressionNode)
    target = NodeListField(Name)
    body = NodeListField(StatementNode)

class Function(StatementNode):
    name = NodeField(FuncNameNode)
    args = NodeListField(Name)
    body = NodeListField(StatementNode)
    varargs = ValueField(bool)

class FunctionLocal(StatementNode):
    name = NodeField(Name)
    args = NodeListField(Name)
    body = NodeListField(StatementNode)
    varargs = ValueField(bool)

class AssignLocal(StatementNode):
    value = NodeListField(ExpressionNode)
    target = NodeListField(Name)

class Return(StatementNode):
    value = NodeListField(ExpressionNode)

class Break(StatementNode):
    pass

class Subscript(VarNode):
    value = NodeField(ExpressionNode)
    slice = NodeField(ExpressionNode)

class Attribute(FuncNameNode):
    value = NodeField(ExpressionNode)
    attr = ValueField(Name)

class Method(FuncNameNode):
    value = NodeField(ExpressionNode)
    method = ValueField(Name)

class NIL(ExpressionNode):
    pass

class FALSE(ExpressionNode):
    pass

class TRUE(ExpressionNode):
    pass

class Number(ExpressionNode):
    n = ValueField(str)

class String(ExpressionNode):
    s = ValueField(str)

class ELLIPSIS(ExpressionNode):
    pass

class Field(Node):
    key = NodeField(ExpressionNode)
    value = NodeField(ExpressionNode)

class Table(ExpressionNode):
    fields = NodeListField(Node) # Field or ExpressionNode

class Lambda(ExpressionNode):
    args = NodeListField(Name)
    body = NodeListField(StatementNode)
    varargs = ValueField(bool)

class BinOp(ExpressionNode):
    op = ValueField(str)
    left = NodeField(ExpressionNode)
    right = NodeField(ExpressionNode)

class UnaryOp(ExpressionNode):
    op = ValueField(str)
    operand = NodeField(ExpressionNode)
