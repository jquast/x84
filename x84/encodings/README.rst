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


Available encodings
-------------------

The following encodings are available:


+-----------+-------------------------------------+-----------------------+
| Name      | Description                         | Aliases               |
+===========+=====================================+=======================+
| amiga     | Amiga Topaz family                  | microknight,          |
|           |                                     | mosoul,               |
|           |                                     | p0tnoodle,            |
|           |                                     | topaz, topaz1,        |
|           |                                     | topaz1plus, topaz2    |
|           |                                     | topaz2plus,           |
|           |                                     | topazplus             |
+-----------+-------------------------------------+-----------------------+
| atarist   | Atari ST familiy                    | atari                 |
+-----------+-------------------------------------+-----------------------+
| cp437     | IBM PC Code Page 437                | ibmpc, ibm_pc,        |
|           |                                     | msdos, pc             |
+-----------+-------------------------------------+-----------------------+
| cp437_art | IBM PC Code Page 437 with some of   | cp437art, ibmpcart,   |
|           | the control characters drawn as     | ibmpc_art, ibm_pc_art,|
|           | glyphs                              | msdos_art, msdosart,  |
|           |                                     | pc_art, pcart         |
+-----------+-------------------------------------+-----------------------+
