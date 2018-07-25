# Classic Game Resource Reader (CGRR): Parse resources from classic games.
# Copyright (C) 2018  Tracy Poff
#
# This file is part of CGRR.
#
# CGRR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CGRR is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CGRR.  If not, see <http://www.gnu.org/licenses/>.
"""Offsets parser format for CGRR."""
import ply.lex as lex
import ply.yacc as yacc

tokens = (
    "BYTE_ORDER",
    "OFFSET",
    "PLAIN_STATEMENT",
)

t_BYTE_ORDER = r'[@=<>!]'

def t_OFFSET(t):
    r"""
    0x[0-9A-Fa-f]+
    """
    t.value = int(t.value, 16)
    return t

t_PLAIN_STATEMENT = r'.+'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t'
t_ignore_COMMENT = r'\#.*'

def t_error(t):
    raise ValueError("Bad input: {}".format(t.value))

def p_statement(p):
    """
    statement : OFFSET PLAIN_STATEMENT
    statement : BYTE_ORDER
    """
    if len(p) == 2:
        p[0] = (None, p[1])
    else:
        p[0] = (p[1], p[2])

def p_error(p):
    raise ValueError("Syntax error in input at line {}, value was {}: {}".format(p.lexer.lineno, p.value, p))

lexer = lex.lex()
parser = yacc.yacc()
