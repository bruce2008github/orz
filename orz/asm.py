try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import imp
import struct
import time
import marshal
from collections import namedtuple


class Type(object):
    NULL = "0"
    NONE = "N"
    FALSE = "F"
    TRUE = "T"
    STOPITER = "S"
    ELLIPSIS = "."
    INT = "i"
    INT64 = "I"
    FLOAT = "f"
    BINARY_FLOAT = "g"
    COMPLEX = "x"
    BINARY_COMPLEX = "y"
    LONG = "l"
    STRING = "s"
    INTERNED = "t"
    STRINGREF = "R"
    TUPLE = "("
    LIST = "["
    DICT = "{"
    CODE = "c"
    UNICODE = "u"
    UNKNOWN = "?"
    SET = "<"
    FROZENSET = ">"

class Flag(object):
    OPTIMIZED = 0x00001
    NEWLOCALS = 0x00002
    VARARGS = 0x00004
    VARKEYWORDS = 0x00008
    NESTED = 0x00010
    GENERATOR = 0x00020
    NOFREE = 0x00040
    GENERATOR_ALLOWED = 0x01000
    FUTURE_DIVISION = 0x02000
    FUTURE_ABSOLUTE_IMPORT = 0x04000
    FUTURE_WITH_STATEMENT = 0x08000
    FUTURE_PRINT_FUNCTION = 0x10000
    FUTURE_UNICODE_LITERALS = 0x20000


class Opcode(object):
    NOP = 9
    POP_TOP = 1
    ROT_TWO = 2
    ROT_THREE = 3
    ROT_FOUR = 5
    DUP_TOP = 4
    UNPACK_SEQUENCE = 92
    DUP_TOPX = 99

    UNARY_POSITIVE = 10
    UNARY_NEGATIVE = 11
    UNARY_NOT = 12
    UNARY_CONVERT = 13
    UNARY_INVERT = 15
    GET_ITER = 68

    BINARY_POWER = 19
    BINARY_MULTIPLY = 20
    BINARY_DIVIDE = 21
    BINARY_FLOOR_DIVIDE = 26
    BINARY_TRUE_DIVIDE = 27
    BINARY_MODULO = 22
    BINARY_ADD = 23
    BINARY_SUBTRACT = 24
    BINARY_SUBSCR = 25
    BINARY_LSHIFT = 62
    BINARY_RSHIFT = 63
    BINARY_AND = 64
    BINARY_XOR = 65
    BINARY_OR = 66
    COMPARE_OP = 107

    INPLACE_POWER = 67
    INPLACE_MULTIPLY = 57
    INPLACE_DIVIDE = 58
    INPLACE_FLOOR_DIVIDE = 28
    INPLACE_TRUE_DIVIDE = 29
    INPLACE_MODULO = 59
    INPLACE_ADD = 55
    INPLACE_SUBTRACT = 56
    INPLACE_LSHIFT = 75
    INPLACE_RSHIFT = 76
    INPLACE_AND = 77
    INPLACE_XOR = 78
    INPLACE_OR = 79

    SLICE = 30 # SLICE+0 +1 +2 +3
    STORE_SLICE = 40 # STORE_SLICE+0 +1 +2 +3
    DELETE_SLICE = 50 # DELETE_SLICE+0 +1 +2 +3
    STORE_SUBSCR = 60
    DELETE_SUBSCR = 61

    LOAD_LOCALS = 82
    LOAD_CONST = 100

    LOAD_NAME = 101
    LOAD_GLOBAL = 116
    LOAD_FAST = 124
    LOAD_DEREF = 136
    LOAD_ATTR = 106
    STORE_NAME = 90
    STORE_GLOBAL = 97
    STORE_FAST = 125
    STORE_DEREF = 137
    STORE_ATTR = 95
    DELETE_NAME = 91
    DELETE_GLOBAL = 98
    DELETE_FAST = 126
    DELETE_ATTR = 96

    LIST_APPEND = 94
    SET_ADD = 146
    MAP_ADD = 147

    BUILD_CLASS = 89
    BUILD_TUPLE = 102
    BUILD_LIST = 103
    BUILD_MAP = 105
    STORE_MAP = 54
    BUILD_SLICE = 133
    BUILD_SET = 104

    LOAD_CLOSURE = 135
    MAKE_CLOSURE = 134
    MAKE_FUNCTION = 132
    CALL_FUNCTION = 131
    CALL_FUNCTION_VAR = 140
    CALL_FUNCTION_KW = 141
    CALL_FUNCTION_VAR_KW = 142

    PRINT_EXPR = 70
    PRINT_ITEM = 71
    PRINT_ITEM_TO = 73
    PRINT_NEWLINE = 72
    PRINT_NEWLINE_TO = 74

    JUMP_FORWARD = 110
    POP_JUMP_IF_TRUE = 115
    POP_JUMP_IF_FALSE = 114
    JUMP_IF_TRUE_OR_POP = 112
    JUMP_IF_FALSE_OR_POP = 111
    JUMP_ABSOLUTE = 113

    RETURN_VALUE = 83
    YIELD_VALUE = 86

    FOR_ITER = 93
    BREAK_LOOP = 80
    CONTINUE_LOOP = 119

    POP_BLOCK = 87
    SETUP_LOOP = 120
    SETUP_EXCEPT = 121
    SETUP_FINALLY = 122

    SETUP_WITH = 143
    WITH_CLEANUP = 81

    RAISE_VARARGS = 130
    END_FINALLY = 88

    IMPORT_NAME = 108
    IMPORT_FROM = 109
    IMPORT_STAR = 84
    EXEC_STMT = 85

    # EXTENDED_ARG = 145

    LABEL = -1

    name = dict((v,k) for (k,v) in locals().items() if v not in (30, 40, 50)) # SLICE, STORE_SLICE, DELETE_SLICE
    name.update(dict((30+i, 'SLICE+%d'%(i)) for i in range(4)))
    name.update(dict((40+i, 'STORE_SLICE+%d'%(i)) for i in range(4)))
    name.update(dict((50+i, 'DELETE_SLICE+%d'%(i)) for i in range(4)))

    hasjrel = ( FOR_ITER, JUMP_FORWARD, SETUP_LOOP, SETUP_EXCEPT, SETUP_FINALLY, SETUP_WITH )
    hasjabs = ( JUMP_ABSOLUTE, JUMP_IF_TRUE_OR_POP, JUMP_IF_FALSE_OR_POP, POP_JUMP_IF_TRUE, POP_JUMP_IF_FALSE, CONTINUE_LOOP )

    HAVE_ARGUMENT = 90


    _stack_effect = {
        NOP: (0, 0),
        POP_TOP: (1, 0),
        ROT_TWO: (2, 2),
        ROT_THREE: (3, 3),
        ROT_FOUR: (4, 4),
        DUP_TOP: (1, 2),
        UNPACK_SEQUENCE: lambda n: (1, n),
        DUP_TOPX: lambda n: (n, n*2),

        UNARY_POSITIVE: (1, 1),
        UNARY_NEGATIVE: (1, 1),
        UNARY_NOT: (1, 1),
        UNARY_CONVERT: (1, 1),
        UNARY_INVERT: (1, 1),
        GET_ITER: (1, 1),

        BINARY_POWER: (2, 1),
        BINARY_MULTIPLY: (2, 1),
        BINARY_DIVIDE: (2, 1),
        BINARY_FLOOR_DIVIDE: (2, 1),
        BINARY_TRUE_DIVIDE: (2, 1),
        BINARY_MODULO: (2, 1),
        BINARY_ADD: (2, 1),
        BINARY_SUBTRACT: (2, 1),
        BINARY_SUBSCR: (2, 1),
        BINARY_LSHIFT: (2, 1),
        BINARY_RSHIFT: (2, 1),
        BINARY_AND: (2, 1),
        BINARY_XOR: (2, 1),
        BINARY_OR: (2, 1),
        COMPARE_OP: (2, 1),

        INPLACE_POWER: (2, 1),
        INPLACE_MULTIPLY: (2, 1),
        INPLACE_DIVIDE: (2, 1),
        INPLACE_FLOOR_DIVIDE: (2, 1),
        INPLACE_TRUE_DIVIDE: (2, 1),
        INPLACE_MODULO: (2, 1),
        INPLACE_ADD: (2, 1),
        INPLACE_SUBTRACT: (2, 1),
        INPLACE_LSHIFT: (2, 1),
        INPLACE_RSHIFT: (2, 1),
        INPLACE_AND: (2, 1),
        INPLACE_XOR: (2, 1),
        INPLACE_OR: (2, 1),

        SLICE+0: (1, 1),
        SLICE+1: (2, 1),
        SLICE+2: (2, 1),
        SLICE+3: (3, 1),
        STORE_SLICE+0: (2, 0),
        STORE_SLICE+1: (3, 0),
        STORE_SLICE+2: (3, 0),
        STORE_SLICE+3: (4, 0),
        DELETE_SLICE+0: (1, 0),
        DELETE_SLICE+1: (2, 0),
        DELETE_SLICE+2: (2, 0),
        DELETE_SLICE+3: (3, 0),
        STORE_SUBSCR: (3, 0),
        DELETE_SUBSCR: (2, 0),

        LOAD_LOCALS: (0, 1),
        LOAD_CONST: (0, 1),

        LOAD_NAME: (0, 1),
        LOAD_GLOBAL: (0, 1),
        LOAD_FAST: (0, 1),
        LOAD_DEREF: (0, 1),
        LOAD_ATTR: (1, 1),
        STORE_NAME: (1, 0),
        STORE_GLOBAL: (1, 0),
        STORE_FAST: (1, 0),
        STORE_DEREF: (1, 0),
        STORE_ATTR: (2, 0),
        DELETE_NAME: (0, 0),
        DELETE_GLOBAL: (0, 0),
        DELETE_FAST: (0, 0),
        DELETE_ATTR: (1, 0),

        LIST_APPEND: (2, 0),
        SET_ADD: (2, 0),
        MAP_ADD: (2, 0),

        BUILD_CLASS: (3, 1),
        BUILD_TUPLE: lambda n: (n, 1),
        BUILD_LIST: lambda n: (n, 1),
        BUILD_MAP: (0, 1),
        STORE_MAP: (3, 1),
        BUILD_SLICE: lambda n: (n, 1),
        BUILD_SET: lambda n: (n, 1),

        LOAD_CLOSURE: (0, 1),
        MAKE_CLOSURE: lambda n: (n+2, 1),
        MAKE_FUNCTION: lambda n: (n+1, 1),
        CALL_FUNCTION: lambda n: ( (n&0xff)+((n>>16)&0xff)*2+1, 1),
        CALL_FUNCTION_VAR: lambda n: ( (n&0xff)+((n>>16)&0xff)*2+2, 1),
        CALL_FUNCTION_KW: lambda n: ( (n&0xff)+((n>>16)&0xff)*2+2, 1),
        CALL_FUNCTION_VAR_KW: lambda n: ( (n&0xff)+((n>>16)&0xff)*2+3, 1),

        PRINT_EXPR: (1, 0),
        PRINT_ITEM: (1, 0),
        PRINT_ITEM_TO: (2, 0),
        PRINT_NEWLINE: (0, 0),
        PRINT_NEWLINE_TO: (1, 0),

        JUMP_FORWARD: (0, 0),
        POP_JUMP_IF_TRUE: (1, 0),
        POP_JUMP_IF_FALSE: (1, 0),
        JUMP_IF_TRUE_OR_POP: (1, 0),
        JUMP_IF_FALSE_OR_POP: (1, 0),
        JUMP_ABSOLUTE: (0, 0),

        RETURN_VALUE: (1, 0),
        YIELD_VALUE: (1, 1),

        FOR_ITER: (1, 2),
        # BREAK_LOOP: (0, 0),
        # CONTINUE_LOOP: (0, 0),

        # POP_BLOCK: (0, 0),
        # SETUP_LOOP: (0, 0),
        # SETUP_EXCEPT: (0, 3),
        # SETUP_FINALLY: (0, 3),

        # SETUP_WITH: (1, 5),
        # WITH_CLEANUP: (2, 1),

        # RAISE_VARARGS: lambda n: (n, 0),
        # END_FINALLY: (1, 0),

        IMPORT_NAME: (2, 1),
        IMPORT_FROM: (1, 1),
        IMPORT_STAR: (1, 0),
        EXEC_STMT: (3, 0),

        # EXTENDED_ARG = 145

        LABEL: (0, 0),
    }

    @classmethod
    def get_stack_effect(self, opcode, arg):
        _stack_effect = self._stack_effect[opcode]

        if callable(_stack_effect):
            return _stack_effect(arg)
        return _stack_effect



class Instruction(object):

    def __init__(self, op, arg=None):
        self.op = op
        self.arg = arg
        self._address = None


    def __str__(self):
        return '%s %s'%(Opcode.name[self.op], self.arg or '')

    __repr__ = __str__


    def _get_address(self):
        return self._address


    def _set_address(self, value):
        if self._address is not None:
            assert value == self._address
            return

        self._address = value


    address = property(_get_address, _set_address)



class Label(Instruction):


    def __init__(self):
        super(Label, self).__init__(Opcode.LABEL)


    def __str__(self):
        return 'LABEL'



def assemble_lnotab(lnotab):
    assert lnotab
    assert lnotab[0][0] == 0

    first_lineno = lnotab[0][1]

    result = []

    for a, b in zip(lnotab[:-1], lnotab[1:]):
        offset, lineno = b[0]-a[0], b[1]-a[1]

        result.append("\xff\x00"*(offset/255))
        offset %= 255

        if lineno < 255:
            result.append(struct.pack("BB", offset, lineno))
            continue

        result.append(struct.pack("BB", offset, 255))
        lineno -= 255

        result.append("\x00\xff"*(lineno/255))
        lineno %= 255

        result.append(struct.pack("BB", 0, lineno))

    return first_lineno, ''.join(result)



class String(object):

    def __init__(self, s, interned=False, ref=None):
        self.s = s
        self.interned = interned
        self.ref = ref
        self.index = -1


    def __eq__(self, other):
        return self.s == other




class StringTable(object):

    def __init__(self):
        self.strings = []


    def add(self, s, interned=False):
        try:
            index = self.strings.index(s)

            ref = self.strings[index]

            # if interned:
            ref.interned = True

            s = String(s, interned, ref)

        except ValueError:
            s = String(s, interned=interned)

        self.strings.append(s)
        return s


    def close(self):
        index = 0

        for s in self.strings[:]:
            if s.ref is None and s.interned:
                s.index = index
                index += 1
            elif s.ref is not None:
                s.ref = s.ref.index
