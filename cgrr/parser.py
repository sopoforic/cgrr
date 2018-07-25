import ply.lex as lex
import ply.yacc as yacc

tokens = (
    "BYTE_ORDER",
    "BUILTIN",
    "NAME",
    "COUNT",
)

t_BYTE_ORDER = r'[@=<>!]'

builtin_dict = {
    'unknown'       : 's',
    'padding'       : 'x',
    'Uint8'         : 'B',
    'int8'          : 'b',
    'Uint16'        : 'H',
    'int16'         : 'h',
    'Uint32'        : 'I',
    'int32'         : 'i',
    'Uint64'        : 'L',
    'int64'         : 'l',
    'float'         : 'f',
    'double'        : 'd',
    'bool'          : '?',
    'char'          : 'c',
    'string'        : 's',
    'pascal_string' : 'p',
}

def t_BUILTIN(t):
    """
    unknown|padding|U?int(?:8|16|32|64)|float|double|bool|char|string|pascal_string
    """
    t.value = builtin_dict[t.value]
    return t

t_NAME = r'[A-Za-z_][A-Za-z0-9_]*'

def t_COUNT(t):
    r'\[\d+\]'
    t.value = int(t.value[1:-1])
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t'
t_ignore_COMMENT = r'\#.*'

def t_error(t):
    raise ValueError("Bad input: {}".format(t.value))

def p_statement(p):
    """
    statement : variable
    statement : byte_order
    """
    p[0] = p[1]

def p_builtin_variable(p):
    """
    variable : BUILTIN NAME
    variable : BUILTIN COUNT NAME
    """
    if len(p) == 3:
        p[0] = ('_BUILTIN', (p[2], p[1]))
    elif len(p) == 4:
        p[0] = ('_BUILTIN', (p[3], str(p[2]) + p[1]))

def p_userdef_variable(p):
    """
    variable : NAME NAME
    variable : NAME COUNT NAME
    """
    if len(p) == 3:
        p[0] = (p[1], (p[2], 's'))
    elif len(p) == 4:
        p[0] = (p[1], (p[3], str(p[2]) + 's'))

def p_byteorder(p):
    """
    byte_order : BYTE_ORDER
    """
    p[0] = ('_BYTE_ORDER', p[1])

def p_error(p):
    raise ValueError("Syntax error in input at line {}, value was {}: {}".format(p.lexer.lineno, p.value, p))

lexer = lex.lex()
parser = yacc.yacc()
