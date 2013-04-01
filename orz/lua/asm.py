from orz.asm import Type, Flag, Opcode, Instruction, Label, String, assemble_lnotab

import marshal
import struct



class Assembly(object):


    def __init__(self, name,
                 names, varnames, freevars, cellvars,
                 argcount=0, varargs=False,
                 parent=None):
        self.name = name
        self.flags = Flag.OPTIMIZED | Flag.NEWLOCALS
        self.argcount = argcount
        self.parent = parent

        if varargs:
            self.flags |= Flag.VARARGS

        self.names = names
        self.varnames = varnames
        self.freevars = freevars
        self.cellvars = cellvars

        if not self.freevars and not self.cellvars:
            self.flags |= Flag.NOFREE
        elif self.freevars:
            self.flags |= Flag.NESTED

        self.instructions = []
        self.consts = []
        self.lnotab = []

        self._last_lineno = 0
        self._last_address = -1
        self._address_count = 0

        self._current_stacksize = 0
        self._max_stacksize = 0


    def set_lineno(self, lineno):
        if lineno >= self._last_lineno:
            if self._address_count == self._last_address:
                self.lnotab = self.lnotab[:-1]

            self.lnotab.append((self._address_count, lineno))
            self._last_lineno = lineno
            self._last_address = self._address_count

    def _get_stacksize(self):
        return self._current_stacksize

    def _set_stacksize(self, value):
        if value > self._max_stacksize:
            self._max_stacksize = value

        self._current_stacksize = value

    stacksize = property(_get_stacksize, _set_stacksize)


    def get_label(self):
        return Label()


    def add_const(self, const):
        for i, c in enumerate(self.consts):
            if const is c:
                return i

        self.consts.append(const)
        return len(self.consts)-1


    def load_const(self, const):
        self.emit(Opcode.LOAD_CONST, self.add_const(const))


    def emit(self, op, arg=None):
        if op >= Opcode.HAVE_ARGUMENT:
            assert arg is not None
        elif op is not Opcode.LABEL:
            assert arg is None

        if op is Opcode.LABEL:
            inst = arg
        else:
            ss_before, ss_after = Opcode.get_stack_effect(op, arg)
            self.stacksize += -ss_before+ss_after

            inst = Instruction(op, arg)

        inst.address = self._address_count

        if inst.op is not Opcode.LABEL:
            if inst.op < Opcode.HAVE_ARGUMENT:
                self._address_count += 1
            else:
                self._address_count += 3

        self.instructions.append(inst)


    def write_string(self, fp, s):
        if s.ref is not None:
            fp.write(Type.STRINGREF)
            fp.write(struct.pack('<L', s.ref))
        else:
            if s.interned:
                fp.write(Type.INTERNED)
            else:
                fp.write(Type.STRING)

            fp.write(struct.pack('<L', len(s.s)))
            fp.write(s.s)


    def serialize(self, fp, filename='<string>'):
        fp.write(Type.CODE)
        fp.write(
            struct.pack(
                '<LLLL',
                self.argcount,
                len(self.varnames)+len(self.cellvars),
                self._max_stacksize,
                self.flags))

        fp.write(Type.STRING)
        fp.write(struct.pack('<L', self._address_count))

        for inst in self.instructions:
            if inst.op is Opcode.LABEL:
                continue

            fp.write(chr(inst.op))
            if inst.op < Opcode.HAVE_ARGUMENT:
                continue

            if inst.op in Opcode.hasjabs:
                arg = inst.arg.address
            elif inst.op in Opcode.hasjrel:
                arg = inst.arg.address - inst.address - 3
            else:
                arg = inst.arg

            fp.write(struct.pack('<H', arg))

        fp.write(Type.TUPLE)
        fp.write(struct.pack('<L', len(self.consts)))


        for const in self.consts:
            if isinstance(const, Assembly):
                const.serialize(fp, filename)
            elif isinstance(const, String):
                self.write_string(fp, const)
            else:
                fp.write(marshal.dumps(const))

        for names in (self.names, self.varnames, self.freevars, self.cellvars):
            fp.write(Type.TUPLE)
            fp.write(struct.pack('<L', len(names)))

            for name in names:
                self.write_string(fp, name.s)

        fp.write(Type.STRING)
        fp.write(struct.pack('<L', len(filename)))
        fp.write(filename)

        self.write_string(fp, self.name.s)

        first_lineno, lnotab = assemble_lnotab(self.lnotab)
        fp.write(struct.pack('<L', first_lineno))

        fp.write(Type.STRING)
        fp.write(struct.pack('<L', len(lnotab)))
        fp.write(lnotab)
