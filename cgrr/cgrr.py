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
import logging
from collections import namedtuple, OrderedDict

from .parser import lexer as cgrr_lexer, parser as cgrr_parser
from .offsets_parser import lexer as offsets_lexer, parser as offsets_parser

logger = logging.getLogger(__name__)

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

            { 'player_name' : (lambda s: s.strip('\\x00')) }

        which would strip null padding from a string.

        Any variables which are not in the dictionaries will be used as-is.

        """
        self.format_def = format
        if isinstance(format, str):
            gs = inspect.currentframe().f_back.f_globals
            f = []
            self.massage_in = {}
            self.massage_out = {}
            self.byte_order = '<'
            for line in format.splitlines():
                if not line.strip():
                    continue
                r = cgrr_parser.parse(line.strip(), lexer=cgrr_lexer)
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
            self.fmt = self.byte_order + "".join(self.format.values())
            self.struct = struct.Struct(self.fmt)
        else:
            self.format = OrderedDict(format)
            self.byte_order = byte_order
            self.fmt = byte_order + "".join(self.format.values())
            self.struct = struct.Struct(self.fmt)
            self.massage_in = massage_in
            self.massage_out = massage_out

    @classmethod
    def from_offsets(cls, format_def):
        """Create a reader by specifying data offsets.

        Construct a file reader with from_offsets(format_def), where format_def
        is a string describing the file format, such as:

            FileReader.from_offsets('''
            <
            0x00 Uint32      score    # Score at index 0x00, before name
            0x04 string[16]  name
            0x14 options[6]  options  # A six byte field with a custom data format
            0x1a EOF
            ''')

        The format of each line is

            OFFSET TYPE VARIABLE_NAME

        or

            OFFSET TYPE[COUNT] VARIABLE_NAME

        The final line of format_def may be:

            FILE_LENGTH EOF

        OFFSET and FILE_LENGTH must be specified in hexadecimal. The number must
        begin with '0x' and may use either capital or lowercase, i.e. 0x1a and
        0x1A are equivalent.

        It is not required to specify offsets in any particular order.

        Optionally, a line may contain a single character describing the
        endianness of the numbers in the file, in the style of struct. By
        default, little-endian ('<') integers are assumed.

        For an explanation of the remaining segment of each line, see the
        documentation for FileReader.

        This function is useful if a file format contains unknown segments,
        because from_offsets will automatically fill in the unknown segments
        with dummy variables. So:

            FileReader.from_offsets('''
            <
            0x00 Uint32      score    # Score at index 0x00, before name
            0x04 string[16]  name
            0x24 options[6]  options  # A six byte field with a custom data format
            0x50 EOF
            ''')
        
        is equivalent to:

            FileReader('''
            <
            Uint32      score   # 0x00-0x03: Score at index 0x00, before name
            string[16]  name    # 0x04-0x13
            unknown[16] unk1    # 0x14-0x23
            options[6]  options # 0x24-0x29: A six byte field with a custom data format
            unknown[38] unk2    # 0x2a-0x4f
            ''')
        
        The EOF statement is not required, but if not specified, the variable
        with the highest offset specified will also be presumed to be the end of
        the file.

        """
        new_format='<\n'
        statements = []
        for line in format_def.splitlines():
            if not line.strip():
                continue
            r = offsets_parser.parse(line.strip(), lexer=offsets_lexer)
            if r[0] == None:
                new_format = r[1] + '\n'
            else:
                statements.append(r)

        logger.debug("Finished parsing offsets format.")

        statements.sort()
        position = 0
        unknowns = 0
        new_lines = []
        max_offset_width = len(hex(statements[-1][0]))-2

        for s in statements:
            if s[0] > position:
                unknowns += 1
                new_lines.append((
                    'unknown[{}]'.format(s[0] - position),
                    'unk{}'.format(unknowns),
                    '# 0x{start:0{mow}x}-0x{end:0{mow}x}'.format(
                        start=position,
                        end=s[0] - 1,
                        mow=max_offset_width,
                    )))
                position = s[0]
            if s[1].strip() == 'EOF':
                break
            stmt = s[1].split(maxsplit=2)
            try:
                stmt_size = struct.calcsize(cgrr_parser.parse(s[1], lexer=cgrr_lexer)[1][1])
            except:
                logger.exception("Failed to parse with cgrr_parser: %r", s[1])
                raise
            position_comment = '# 0x{start:0{mow}x}-0x{end:0{mow}x}'.format(
                start=position,
                end=position + stmt_size - 1,
                mow=max_offset_width)
            if len(stmt) == 2:
                stmt.append(position_comment)
            else:
                stmt[2] = position_comment + ': ' + stmt[2][1:].strip()
            new_lines.append(stmt)
            position += stmt_size
        max_left = max(len(s[0]) for s in new_lines)
        max_mid = max(len(s[1]) for s in new_lines)
        for l in new_lines:
            new_format += "{left:<{max_left}} {mid:<{max_mid}} {right}\n".format(
                left=l[0],
                mid=l[1],
                right=l[2],
                max_left=max_left,
                max_mid=max_mid)
        logger.debug("from_offsets completed. New format: \n\n%s", new_format)
        return cls(new_format)

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
