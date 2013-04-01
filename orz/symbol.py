class Symbol(object):
    slot = None

    def __init__(self, name):
        self.name = name


class Attribute(Symbol):

    def __eq__(self, other):
        return other.__class__ is Attribute and self.name == other.name


class Global(Symbol):

    def __eq__(self, other):
        return other.__class__ is Global and self.name == other.name


class Free(Symbol):

    def __init__(self, name, parent):
        super(Free, self).__init__(name)
        self.parent = parent

    def __eq__(self, other):
        return other.__class__ is Free and self.name == other.name and self.parent == other.parent


class Local(Symbol):
    is_referenced = False


class Name(Symbol):

    def __eq__(self, other):
        return self.name == other.name


def calculate_slots(symbols):
    names = []
    varnames = []
    freevars = []
    cellvars = []

    for symbol in symbols:
        if isinstance(symbol, Global) or isinstance(symbol, Attribute):
            if symbol not in names:
                names.append(Name(symbol.name))
            symbol.slot = names.index(symbol)

        elif isinstance(symbol, Free):
            if symbol not in freevars:
                freevars.append(symbol)

        elif isinstance(symbol, Local):
            if symbol.is_referenced:
                slot = len(cellvars)
                cellvars.append(symbol)
            else:
                slot = len(varnames)
                varnames.append(symbol)

            symbol.slot = slot

    for symbol in symbols:
        if isinstance(symbol, Free):
            symbol.slot = len(cellvars) + freevars.index(symbol)

    return names, varnames, freevars, cellvars
