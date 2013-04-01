from orz.parse import SyntaxParser
from . import ast

import re

ESCAPE_RE = re.compile(r"\\[abfnrtv\\\"']|\\z\s*|\\x[0-9a-fA-F]{2}|\\\d{1,3}")


def escape(string):
    def replace(match):
        s = match.group(0)
        c = s[1]

        if c in "\"'\\":
            return c
        elif c in "abfnrtv":
            return s.decode("string_escape")
        elif c == 'z':
            return ''
        elif c == 'x':
            return chr(int(s[2:], 16))
        else:
            o = int(s[1:])
            if o > 255:
                raise Exception("decimal escape too large near '%s'"%(s))

            return chr(o)

    return ESCAPE_RE.sub(replace, string)


class Parser(SyntaxParser):
    t_SHEBANG = r'^\#![^\n]*'
    t_NUMBER = r'0[xX](?:[0-9A-Fa-f]+(?:\.[0-9A-Fa-f]+)?|\.[0-9A-Fa-f]+)(?:[pP][+-]?\d+)?|(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?'
    t_CONCAT = r'\.\.'
    t_ELLIPSIS = r'\.\.\.'
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_POWER = r'\^'
    t_MOD = r'%'
    t_LT = r'<'
    t_GT = r'>'
    t_LE = r'<='
    t_GE = r'>='
    t_EQ = r'=='
    t_NE = r'~='
    t_LEN = r'\#'
    t_LABEL = r'::'
    t_ignore = ' \t'
    t_ignore_comment = r'--[^\n]*(?=\n|$)'

    literals = ['=', '(', ')', '{', '}', '[', ']', ';', ':', ',', '.']
    reserved = [
        'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
        'goto', 'function', 'if', 'in', 'local', 'nil', 'not', 'or',
        'repeat', 'return', 'then', 'true', 'until', 'while' ]


    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('nonassoc', 'LT', 'GT', 'LE', 'GE', 'EQ', 'NE'),
        ('left', 'CONCAT'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD'),
        ('right', 'NOT', 'LEN', 'UMINUS'),
        ('right', 'POWER')
    )


    CONSTANTS = {
        'true': ast.TRUE,
        'false': ast.FALSE,
        'nil': ast.NIL}


    def t_NAME(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        t.type = t.value.upper() if t.value in self.reserved else 'NAME'
        return t


    def t_STRING(self, t):
        r"\"(?:[^\"\n\\]|\\[abfnrtv\\\"]|\\z\s*|\\x[0-9a-fA-F]{2}|\\\d{1,3})*\"|'(?:[^'\n\\]|\\[abfnrtv\']|\\z\s*|\\x[0-9a-fA-F]{2}|\\\d{1,3})*'"
        t.value = escape(t.value[1:-1])
        return t


    def t_LONGSTRING(self, t):
        r'\[(?P<b>=*)\[(?:(?!\](?P=b)\]).|\n)*\](?P=b)\]'
        t.lexer.lineno += t.value.count('\n')

        i = t.value.find('[', 1)+1
        t.value = t.value[i:-i]

        if t.value.startswith("\n"):
            t.value = t.value[1:]

        return t


    def t_ignore_long_comment(self, t):
        r'--\[(?P<c>=*)\[(?:(?!\](?P=c)\]).|\n)*\](?P=c)\]'
        t.lexer.lineno += t.value.count('\n')


    def t_ignore_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)


    def p_file_with_shebang(self, p):
        """file : SHEBANG block"""
        p[0] = ast.File(body=p[2], **self.position(p,2))


    def p_file(self, p):
        """file : block"""
        p[0] = ast.File(body=p[1], **self.position(p,1))


    def p_block(self, p):
        """block : stat block"""
        p[0] = [p[1]] + p[2]


    def p_block_sep(self, p):
        """block : stat ';' block"""
        p[0] = [p[1]] + p[3]


    def p_block_laststat(self, p):
        """block : retstat
                 | retstat ';'"""
        p[0] = [p[1]]


    def p_block_empty(self, p):
        """block : """
        p[0] = []


    def p_stat_assign(self, p):
        """stat : varlist '=' explist"""
        p[0] = ast.Assign(
            target=p[1],
            value=p[3],
            **self.position(p,1))


    def p_stat_functioncall(self, p):
        """stat : functioncall"""
        p[0] = ast.CallStatement(
            body=p[1],
            **self.position(p,1))


    def p_stat_label(self, p):
        """stat : LABEL name LABEL"""
        p[0] = ast.Label(
            name = p[2].id,
            **self.position(p,1))


    def p_stat_break(self, p):
        """stat : BREAK"""
        p[0] = ast.Break(**self.position(p,1))


    def p_stat_goto(self, p):
        """stat : GOTO name"""
        p[0] = ast.Goto(target=p[2].id, **self.position(p,1))


    def p_stat_block(self, p):
        """stat : DO block END"""
        p[0] = ast.Block(
            body=p[2],
            **self.position(p,1))


    def p_stat_while(self, p):
        """stat : WHILE exp DO block END"""
        p[0] = ast.While(
            test=p[2],
            body=p[4],
            **self.position(p,1))


    def p_stat_repeat(self, p):
        """stat : REPEAT block UNTIL exp"""
        p[0] = ast.Repeat(
            body=p[2],
            test=p[4],
            **self.position(p,1))


    def p_stat_if(self, p):
        """stat : IF exp THEN block ifstat"""
        p[0] = ast.If(
            test=p[2],
            body=p[4],
            orelse=p[5],
            **self.position(p,1))


    def p_ifstat_elseif(self, p):
        """ifstat : ELSEIF exp THEN block ifstat"""
        p[0] = ast.If(
            test=p[2],
            body=p[4],
            orelse=p[5],
            **self.position(p,1))


    def p_ifstat_else(self, p):
        """ifstat : ELSE block END"""
        p[0] = p[2]


    def p_ifstat_end(self, p):
        """ifstat : END"""
        p[0] = []


    def p_stat_for(self, p):
        """stat : FOR name '=' exp ',' exp DO block END"""
        p[0] = ast.For(
            target = p[2],
            start = p[4],
            stop = p[6],
            step = ast.Number(n="1", **self.position(p, 7)),
            body = p[8],
            **self.position(p,1))


    def p_stat_forstep(self, p):
        """stat : FOR name '=' exp ',' exp ',' exp DO block END"""
        p[0] = ast.For(
            target=p[2],
            start=p[4],
            stop=p[6],
            step=p[8],
            body=p[10],
            **self.position(p,1))


    def p_stat_foreach(self, p):
        """stat : FOR namelist IN explist DO block END"""
        p[0] = ast.ForEach(
            target=p[2],
            iter=p[4],
            body=p[6], **self.position(p,1))


    def p_stat_function(self, p):
        """stat : FUNCTION funcname funcbody"""
        args = p[3][0]

        if isinstance(p[2], ast.Method):
            args = [ast.Name(id='self', **self.position(p,3))] + args

        p[0] = ast.Function(
            name=p[2],
            args=args,
            body=p[3][1],
            varargs=p[3][2],
            **self.position(p,1))


    def p_stat_local_function(self, p):
        """stat : LOCAL FUNCTION name funcbody"""
        p[0] = ast.FunctionLocal(
            name=p[3],
            args=p[4][0],
            body=p[4][1],
            varargs=p[4][2],
            **self.position(p,1))


    def p_stat_local(self, p):
        """stat : LOCAL namelist"""
        p[0] = ast.AssignLocal(
            target=p[2],
            value=[],
            **self.position(p,1))


    def p_stat_local_assign(self, p):
        """stat : LOCAL namelist '=' explist"""
        p[0] = ast.AssignLocal(
            target=p[2],
            value=p[4],
            **self.position(p,1))


    def p_retstat(self, p):
        """retstat : RETURN explist
                   | RETURN emptylist"""
        p[0] = ast.Return(
            value=p[2],
            **self.position(p,1))


    def p_funcname(self, p):
        """funcname : funcnamehead"""
        p[0] = p[1]


    def p_funcname_method(self, p):
        """funcname : funcnamehead ':' name"""
        p[0] = ast.Method(
            value = p[1],
            method = p[3],
            **self.position(p,1))


    def p_funcnamehead(self, p):
        """funcnamehead : funcnamehead '.' name"""
        p[0] = ast.Attribute(
            value = p[1],
            attr = p[3],
            **self.position(p,1))


    def p_funcnamehead_single(self, p):
        """funcnamehead : name"""
        p[0] = p[1]


    def p_varlist(self, p):
        """varlist : varlist ',' var"""
        p[0] = p[1] + [p[3]]


    def p_varlist_single(self, p):
        """varlist : var"""
        p[0] = [p[1]]


    def p_var_name(self, p):
        """var : name"""
        p[0] = p[1]


    def p_var_subscript(self, p):
        """var : prefixexp '[' exp ']'"""
        p[0] = ast.Subscript(
            value=p[1],
            slice=p[3],
            **self.position(p,1))


    def p_var_attribute(self, p):
        """var : prefixexp '.' name"""
        p[0] = ast.Attribute(
            value=p[1],
            attr=p[3],
            **self.position(p,1))


    def p_namelist(self, p):
        """namelist : namelist ',' name"""
        p[0] = p[1] + [p[3]]


    def p_namelist_single(self, p):
        """namelist : name"""
        p[0] = [p[1]]


    def p_explist(self, p):
        """explist : explist ',' exp """
        p[0] = p[1] + [p[3]]


    def p_explist_single(self, p):
        """explist : exp"""
        p[0] = [p[1]]


    def p_exp_constant(self, p):
        """exp : NIL
               | TRUE
               | FALSE"""
        p[0] = self.CONSTANTS[p[1]](**self.position(p,1))


    def p_exp_number(self, p):
        """exp : NUMBER"""
        p[0] = ast.Number(n=p[1], **self.position(p,1))


    def p_exp(self, p):
        """exp : ellipsis
               | functiondef
               | prefixexp
               | tableconstructor
               | string"""
        p[0] = p[1]


    def p_exp_binops(self, p):
        """exp : exp PLUS exp
               | exp MINUS exp
               | exp TIMES exp
               | exp DIVIDE exp
               | exp POWER exp
               | exp MOD exp
               | exp CONCAT exp
               | exp LT exp
               | exp LE exp
               | exp GT exp
               | exp GE exp
               | exp EQ exp
               | exp NE exp
               | exp AND exp
               | exp OR exp"""
        p[0] = ast.BinOp(
            left = p[1],
            op = p[2],
            right = p[3],
            **self.position(p,1))


    def p_exp_unops(self, p):
        """exp : NOT exp
               | LEN exp
               | MINUS exp %prec UMINUS"""
        p[0] = ast.UnaryOp(
            op = p[1],
            operand = p[2],
            **self.position(p,1))


    def p_prefixexp_var(self, p):
        """prefixexp : var
                     | functioncall"""
        p[0] = p[1]


    def p_prefixexp_exp(self, p):
        """prefixexp : '(' exp ')'"""
        p[0] = p[2]


    def p_functioncall(self, p):
        """functioncall : prefixexp args"""
        p[0] = ast.Call(
            func=p[1],
            args=p[2],
            **self.position(p,1))


    def p_methodcall(self, p):
        """functioncall : prefixexp ':' name args"""
        p[0] = ast.Call(
            func = ast.Method(
                value = p[1],
                method = p[3],
                **self.position(p,1)),
            args = p[4],
            **self.position(p,1))


    def p_args_explist(self, p):
        """args : '(' explist ')'
                | '(' emptylist ')'"""
        p[0] = p[2]


    def p_args(self, p):
        """args : tableconstructor
                | string"""
        p[0] = [p[1]]


    def p_functiondef(self, p):
        """functiondef : FUNCTION funcbody"""
        p[0] = ast.Lambda(
            args = p[2][0],
            body = p[2][1],
            varargs = p[2][2],
            **self.position(p,1))


    def p_funcbody(self, p):
        """funcbody : '(' namelist ')' block END
                    | '(' emptylist ')' block END"""
        p[0] = p[2], p[4], False


    def p_funcbody_with_ellipsis(self, p):
        """funcbody : '(' namelist ',' ellipsis ')' block END"""
        p[0] = p[2], p[6], True


    def p_funcbody_ellipsis(self, p):
        """funcbody : '(' ellipsis ')' block END"""
        p[0] = [], p[4], True


    def p_ellipsis(self, p):
        """ellipsis : ELLIPSIS"""
        p[0] = ast.ELLIPSIS(**self.position(p,1))


    def p_tableconstructor(self, p):
        """tableconstructor : '{' fieldlist '}'
                            | '{' emptylist '}'"""
        assert all(
            isinstance(f, ast.Field) or
            isinstance(f, ast.ExpressionNode)
            for f in p[2])

        p[0] = ast.Table(fields=p[2], **self.position(p,1))


    def p_fieldlist(self, p):
        """fieldlist : fieldlisthead
                     | fieldlisthead fieldsep"""
        p[0] = p[1]


    def p_fieldlisthead(self, p):
        """fieldlisthead : fieldlisthead fieldsep field"""
        p[0] = p[1] + [p[3]]


    def p_fieldlisthead_single(self, p):
        """fieldlisthead : field"""
        p[0] = [p[1]]


    def p_field_subscript(self, p):
        """field : '[' exp ']' '=' exp"""
        p[0] = ast.Field(
            key = p[2],
            value = p[5],
            **self.position(p,1))


    def p_field(self, p):
        """field : name '=' exp"""
        p[0] = ast.Field(
            key = ast.String(
                s=p[1].id,
                **self.position(p,1)),
            value = p[3],
            **self.position(p,1))


    def p_field_exp(self, p):
        """field : exp"""
        p[0] = p[1]


    def p_fieldsep(self, p):
        """fieldsep : ','
                    | ';'"""
        pass


    def p_name(self, p):
        """name : NAME"""
        p[0] = ast.Name(id=p[1], **self.position(p,1))


    def p_emptylist(self, p):
        """emptylist : """
        p[0] = []


    def p_string(self, p):
        """string : STRING
                  | LONGSTRING"""
        p[0] = ast.String(s=p[1], **self.position(p,1))
