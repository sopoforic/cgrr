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
    def __init__(self, format, byte_order="<", encoding="ascii"):
        """Create a reader for a specific file format.

        format should be a list of tuples in the form

        (name, format_string)

        where format_string is a struct-style description of the variable.

        """
        self.format = OrderedDict(format)
        self.byte_order = byte_order
        self.encoding = encoding
        self.fmt = byte_order + "".join(self.format.values())
        self.struct = struct.Struct(self.fmt)

    def unpack(self, data):
        vals = self.struct.unpack(data)
        dictionary = dict(zip(
            filter(lambda x: x[:7] != 'padding', self.format.keys()), vals))
        for k in dictionary:
            if type(dictionary[k]) is bytes and k[:3] != "raw":
                dictionary[k] = dictionary[k].decode(self.encoding).strip('\x00')
        return dictionary

    def pack(self, data):
        for k in data:
            if type(data[k]) is string:
                data[k] = data[k].encode(self.encoding)
        vals = [data[key] for key in
                filter(lambda x: x[:7] != 'padding', self.format.keys())]
        return self.struct.pack(vals)
