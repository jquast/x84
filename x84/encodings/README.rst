X/84 encodings
==============

These files use the py:`encodings` and py:`codecs` API to provide translation
maps between character sets.


Usage
-----

In order to use the translation maps, you can just simply use::

    >>> amiga_art = file('test.asc').read().decode('topaz')

Now ``amiga_art`` will be a properly encoded unicode object, suitable for
sending to the client (where it will either be re-encoded as UTF-8 or CP437).
