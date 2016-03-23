# What is this project?

cgrr.py holds utility functions used by other modules for parsing game
resource files.

# What does it do?

At present, cgrr.py provides three things:

1. `verify`, a simple function to verify that certain files exist in a path
2. `File`, a namedtuple to be used with `verify`
3. `FileReader`, a class used for reading files into dictionaries

## verify

Pass this function a list of files (instances of the `File` namedtuple) and a
path and it will verify that those files exist in that path. It is intended to
be used to verify that a certain program resides in the given path, e.g. by
checking that the program's main executable is in the expected place.

```python
identifying_files = [
    File("ARCHERY.EXE", 31616,  "d8fae202edcc48d51a72026cbfbe7fa8"),
]
path = "path/to/archery"
verify(identifying_files, path)
```

The call to `verify` above will return `True` iff a file
`path/to/archery/ARCHERY.EXE` exists, is `31,616` bytes, and has md5 hash
`d8fae202edcc48d51a72026cbfbe7fa8`. If `identifying_files` contains multiple
`File` namedtuples, *all* of the files described in the list must be present.

## File

`File` is simply a namedtuple representing a file. The fields of the namedtuple
are `path`, `size`, and `md5`.

To create a new `File`:

```python
example = File("path/to/example.tle", 12345, "0123456789abcdef0123456789abcdef")
```

The path should be given relative to some base path (e.g. the main path to the
program to be identified by that file) which will be passed to `verify`
separately.

`size` is the file size in bytes.

`md5` is the md5 hash of the file.

## FileReader

FileReader is a factory that produces readers for specific file formats. A
reader provides two methods, `pack` and `unpack`, used for parsing and
unparsing data from files. Under the hood, it uses the `struct` module.

Construct a file reader with `FileReader(format)`, where `format` is a
string describing the file format, such as:

```python
score_reader = FileReader("""
<
Uint32      score         # Score at index 0x00, before name
string[16]  name
options[6]  game_options  # A six byte field with a custom data format
""")
```

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

The `Struct` used by this module can be accessed directly as
`score_reader.struct`, if desired.

The reader specified above will extract three variables from a 26-byte
file: `score`, a (little-endian) 32-bit unsigned integer; `name`, a
16-byte string; and `game_options`, a 6-byte field in a custom format.

Given a file in the required format, the file can be parsed with:

```python
data = scorefile.read(26)
scores = score_reader.unpack(data)
```

which will produce `scores`, a dictionary with three entries

```python
scores = {"name" : "SomeName", "score" : 1234, "game_options" : b'......'}
```

Given a dictionary with these entries, `pack` can be used to generate a
scorefile in the original format.

```python
data = score_reader.pack( {"name" : "Cheater",
                           "score" : 9999,
                           "game_options" : b'......'} )
scorefile.write(data)
```

Since we didn't define `parse_options` and `unparse_options` functions,
the six bytes devoted to that variable are simply assigned directly. It
might be more useful to parse the options, however:

```python
def parse_options(b):
    return { 'option' + str(i) : b[i] for i in range(6) }

def unparse_options(o):
    return bytes([o['option' + str(i)] for i in range(6)])
```

# What is it good for?

cgrr.py is used by other modules in the CGRR project. For example:

* [cgrr-gameboy](https://github.com/sopoforic/cgrr-gameboy), which reads
    and edits Game Boy ROM headers
* [cgrr-gamecube](https://github.com/sopoforic/cgrr-gamecube), which reads
    and edits GameCube GCI files
* [cgrr-mariospicross](https://github.com/sopoforic/cgrr-mariospicross),
    which reads and edits puzzles for the Game Boy game Mario's Picross
* [cgrr-pokemon](https://github.com/sopoforic/cgrr-pokemon), which reads
    and edits save files for Pokemon games

# License

CGRR is available under the GPL v3 or later. See the file COPYING for details.
