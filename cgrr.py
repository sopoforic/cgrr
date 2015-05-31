# Classic Game Resource Reader (CGRR): Parse resources from classic games.
# Copyright (C) 2014  Tracy Poff
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
"""Utilities for cgrr."""
import os
import hashlib
import struct

from collections import namedtuple, OrderedDict

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
        # If the data needs processing before being sent to the user, then the
        # user should have passed a dictionary massage_in with entries like
        #
        #     { 'variable_name' : processing_function }
        #
        # which can be used to massage the data into the desired format. This
        # should be paired with a massage_out dictionary (used by pack) to
        # turn things back into the required format.
        #
        # An example input processing function might be:
        #
        #     { 'player_name' : (lambda s: s.strip('\x00')) }
        #
        # which would strip null padding from a string.
        #
        # Any variables which are not in the dictionary will be used as-is.
        if self.massage_in:
            for k in dictionary:
                if k in self.massage_in:
                    dictionary[k] = self.massage_in[k](dictionary[k])
        return dictionary

    def pack(self, dictionary):
        # See the comment on unpack.
        out = {}
        if self.massage_out:
            for k in dictionary:
                if k in self.massage_out:
                    out[k] = self.massage_out[k](dictionary[k])
                else:
                    out[k] = dictionary[k]
        else:
            out = dictionary
        vals = [out[key] for key in
                filter(lambda x: x[:7] != 'padding', self.format.keys())]
        return self.struct.pack(*vals)
