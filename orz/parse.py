import os.path
import sys
from ply import lex, yacc



class SyntaxParser(object):
    reserved = []


    def __init__(self, filename):
        self.filename = filename
        self.tokens = [ r.upper() for r in self.reserved ] + [ a[2:] for a in dir(self) if a[:2] == 't_' and a[2:].isupper() ]
        self.lexer = lex.lex(module=self, debug=False)
        self.parser = yacc.yacc(
            module=self,
            debug=False,
            write_tables=False,
            picklefile=os.path.splitext(
                sys.modules[self.__class__.__module__].__file__
                )[0]+'.parsetab')


    def t_error(self, t):
        raise SyntaxError(
            "Illegal character '%s'!" % t.value[0],
            ( self.filename,
              t.lineno,
              self.col_offset(t.lexpos),
              self.line_of(t)
            ))


    def p_error(self, p):
        raise SyntaxError(
            "Invalid Syntax",
            ( self.filename,
              p.lineno,
              self.col_offset(p.lexpos),
              self.line_of(p)
            ))


    def line_of(self, t):
        last_cr = self.lexer.lexdata.rfind('\n', 0, t.lexpos)
        next_cr = self.lexer.lexdata.find('\n', t.lexpos)
        if next_cr < 0:
            next_cr = None
        return self.lexer.lexdata[last_cr+1: next_cr]


    def col_offset(self, lexpos):
        last_cr = self.lexer.lexdata.rfind('\n', 0, lexpos)
        if last_cr < 0:
            last_cr = 0
        return lexpos - last_cr


    def position(self, p, i):
        return {
            'lineno': p.lineno(i),
            'col_offset': self.col_offset(p.lexpos(i))}


    def parse(self, data):
        return self.parser.parse(data, lexer=self.lexer, tracking=True)
