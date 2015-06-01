What is this project?
=====================

cgrr.py holds utility functions used by other modules for parsing game
resource files.

What does it do?
================

At present, cgrr.py provides three things:

1. `verify`, a simple function to verify that certain files exist in a path
2. `File`, a namedtuple to be used with `verify`
3. `FileReader`, a class used for reading files into dictionaries

verify
------

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

File
----

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

FileReader
----------

FileReader is a factory that produces readers for specific file formats. A
reader provides two methods, `pack` and `unpack`, used for parsing and unparsing
data from files. Under the hood, it uses the `struct` module.

```python
score_reader = FileReader(
    format = [
        ("name", "9s"),
        ("score", "4s"),
    ],
    massage_in = {
        "name"  : (lambda s: s.decode('ascii').strip()),
        "score" : (lambda s: int(s.decode('ascii'))),
    },
    massage_out = {
        "name"  : (lambda s: s.ljust(9).encode('ascii')),
        "score" : (lambda s: str(s).rjust(4).encode('ascii')),
    },
)
```

The `Struct` used by this module can be accessed directly as
`score_reader.struct`, if desired.

This reader will extract two variables from a 13-byte file: `name`, a nine
character string, and `score`, an integer of up to four digits stored in text
form in the file.

The dictionaries `massage_in` and `massage_out` provide functions to parse the
raw data from the file into a usable form and to unparse the data back into the
correct raw form.

Given a file containing a single score in the required format, the file can be
parsed with:

```python
data = scorefile.read(13)
scores = score_reader.unpack(data)
```

which will produce `scores`, a dictionary with two entries

```python
score = {"name" : "SomeName", "score" : 1234}
```

Given a dictionary with these entries, `pack` can be used to generate a
scorefile in the original format.

```python
data = score_reader.pack( {"name" : "Cheater", "score" : 9999} )
scorefile.write(data)
```

License
=======

CGRR is available under the GPL v3 or later. See the file COPYING for details.
