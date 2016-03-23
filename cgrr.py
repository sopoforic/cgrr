# Classic Game Resource Reader (CGRR): Parse resources from classic games.
# Copyright (C) 2014-2016  Tracy Poff
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
"""Utilities for cgrr modules."""
import os
import hashlib
import struct
import inspect

import ply.lex as lex
import ply.yacc as yacc

from collections import namedtuple, OrderedDict

tokens = (
    "BYTE_ORDER",
    "BUILTIN",
    "NAME",
    "COUNT",
    "COMMENT",
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
    raise ValueError("Syntax error in input: {}".format(p))

def verify(identifying_files, path):
    """Verifies that the files in identifying_files are present in path.

    Files must match size and md5 checksum.

    """
    for idfile in identifying_files:
        try:
            if os.path.getsize(os.path.join(path, idfile.path)) != idfile.size:
                return False
            with open(os.path.join(path, idfile.path), "rb") as realfile:
                hasher = hashlib.md5()
                hasher.update(realfile.read())
                if hasher.hexdigest() != idfile.md5:
                    return False
        except OSError:
            return False
    return True

File = namedtuple("File", ["path", "size", "md5"])

class FileReader(object):
    """Reads files into dictionaries."""
    def __init__(self, format, massage_in=None, massage_out=None, byte_order="<"):
        """Create a reader for a specific file format.
        
        Construct a file reader with FileReader(format), where format is a
        string describing the file format, such as:
        
            FileReader('''
            <
            Uint32      score    # Score at index 0x00, before name
            string[16]  name
            options[6]  options  # A six byte field with a custom data format
            ''')
        
        The format of each line is
        
            TYPE VARIABLE_NAME
        
        or
        
            TYPE[COUNT] VARIABLE_NAME
        
        If COUNT is not specified, it defaults to 1.
        
        Optionally, a line may contain a single character describing the
        endianness of the numbers in the file, in the style of struct. By
        default, little-endian ('<') integers are assumed.
        
        Characters following a pound sign ('#') are treated as comments and
        ignored.
        
        If TYPE is one of the builtin types supported by the struct module (e.g.
        Uint16), it will be processed by struct. For builtin types, COUNT is
        treated as the repeat count for struct: Uint32[4] means four 32-bit
        unsigned integers (16 bytes), and string[4] means a 4 byte string.
        
        Otherwise, TYPE is treated as a user-defined type. Then COUNT is the
        number of bytes occupied by the variable, and the FileReader will look
        for a function named parse_TYPE (e.g. parse_options) when unpacking the
        data. If found, the function will be called with the bytestring as an
        argument and the return value assigned as the value of the variable.
        Similarly, the FileReader will pass the variable to a function named
        unparse_TYPE (e.g. unparse_options) which should return a bytestring of
        length COUNT when packing the data. If those functions are not defined,
        the bytes will be returned as-is.
        
        For compatibility reasons, it is possible to specify FileReaders using
        cgrr 1.1 style lists and dicts. In that case:

        format should be a list of tuples in the form

        (variable_name, format_string)

        where format_string is a struct-style description of the variable.

        If present, massage_in and massage_out should be dictionaries mapping
        (a subset of) the variable names from format to functions that massage
        the raw value into a user-friendly format and from said user-friendly
        format back into the raw data required by the file, respectively.

        An example input processing function might be:

            { 'player_name' : (lambda s: s.strip('\x00')) }

        which would strip null padding from a string.

        Any variables which are not in the dictionaries will be used as-is.

        """
        if isinstance(format, str):
            gs = inspect.currentframe().f_back.f_globals
            lex.lex()
            parser = yacc.yacc()
            f = []
            self.massage_in = {}
            self.massage_out = {}
            self.byte_order = '<'
            for line in format.splitlines():
                if not line:
                    continue
                r = parser.parse(line)
                if not r:
                    continue
                if r[0] == '_BUILTIN':
                    f.append(r[1])
                elif r[0] == '_BYTE_ORDER':
                    self.byte_order = r[1]
                else:
                    self.massage_in[r[1][0]] = gs.get('parse_' + r[0], lambda x: x)
                    self.massage_out[r[1][0]] = gs.get('unparse_' + r[0], lambda x: x)
                    f.append(r[1])
            self.format = OrderedDict(f)
            self.fmt = byte_order + "".join(self.format.values())
            self.struct = struct.Struct(self.fmt)
        else:
            self.format = OrderedDict(format)
            self.byte_order = byte_order
            self.fmt = byte_order + "".join(self.format.values())
            self.struct = struct.Struct(self.fmt)
            self.massage_in = massage_in
            self.massage_out = massage_out

    def unpack(self, data):
        vals = self.struct.unpack(data)
        dictionary = dict(zip(
            filter(lambda x: x[:7] != 'padding', self.format.keys()), vals))
        if self.massage_in:
            for k in dictionary:
                if k in self.massage_in:
                    if callable(self.massage_in[k]):
                        dictionary[k] = self.massage_in[k](dictionary[k])
                    else:
                        dictionary[k] = self.massage_in[k].unpack(dictionary[k])
        return dictionary

    def pack(self, dictionary):
        out = {}
        if self.massage_out:
            for k in dictionary:
                if k in self.massage_out:
                    if callable(self.massage_out[k]):
                        out[k] = self.massage_out[k](dictionary[k])
                    else:
                        out[k] = self.massage_out[k].pack(dictionary[k])
                else:
                    out[k] = dictionary[k]
        else:
            out = dictionary
        vals = [out[key] for key in
                filter(lambda x: x[:7] != 'padding', self.format.keys())]
        return self.struct.pack(*vals)

class UnsupportedSoftwareException(Exception):
    """Indicates that the module doesn't support the software passed to it."""
    pass
