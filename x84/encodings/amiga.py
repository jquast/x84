"""
Amiga "Topaz" codec for x/84.

There is no provided unicode translation map, but we try to approximate the
Topaz font families as close as possible.
"""

from __future__ import absolute_import

import codecs
import encodings
import encodings.aliases

# Codec APIs


class Codec(codecs.Codec):

    def decode(self, input, errors='strict'):
        return codecs.charmap_decode(input, errors, decoding_table)

    def encode(self, input, errors='strict'):
        raise NotImplementedError()


class IncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, input, final=False):
        raise NotImplementedError()


class IncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, input, final=False):
        return codecs.charmap_decode(input, self.errors, decoding_table)[0]


class StreamReader(Codec, codecs.StreamReader):
    pass


class StreamWriter(Codec, codecs.StreamWriter):
    pass


# encodings module API

def getaliases():
    return (
        'microknight',
        'mosoul',
        'p0tnoodle',
        'topaz',
        'topaz1',
        'topaz1plus',
        'topaz2',
        'topaz2plus',
        'topazplus',
    )


def getregentry():
    return codecs.CodecInfo(
        name='topaz',
        encode=Codec().encode,
        decode=Codec().decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


encodings._cache['topaz'] = getregentry()


# Decoding Table

decoding_map = codecs.make_identity_dict(range(256))
decoding_map.update({
    0x002d: 0x2500,     # BOX DRAWINGS LIGHT HORIZONTAL
    0x002f: 0x2571,     # BOX DRAWINGS LIGHT DIAGONAL UPPER RIGHT TO LOWER LEFT
    0x0058: 0x2573,     # BOX DRAWINGS LIGHT DIAGONAL CROSS
    0x005c: 0x2572,     # BOX DRAWINGS LIGHT DIAGONAL UPPER LEFT TO LOWER RIGHT
    0x005f: 0x2581,     # LOWER ONE EIGHTH BLOCK
    0x007c: 0x2502,     # BOX DRAWINGS LIGHT VERTICAL
    0x007f: 0x259e,     # QUADRANT UPPER RIGHT AND LOWER LEFT
    0x0080: 0x2b1c,     # WHITE LARGE SQUARE
    0x0081: 0x2b1c,     # WHITE LARGE SQUARE
    0x0082: 0x2b1c,     # WHITE LARGE SQUARE
    0x0083: 0x2b1c,     # WHITE LARGE SQUARE
    0x0084: 0x2b1c,     # WHITE LARGE SQUARE
    0x0085: 0x2b1c,     # WHITE LARGE SQUARE
    0x0086: 0x2b1c,     # WHITE LARGE SQUARE
    0x0087: 0x2b1c,     # WHITE LARGE SQUARE
    0x0088: 0x2b1c,     # WHITE LARGE SQUARE
    0x0089: 0x2b1c,     # WHITE LARGE SQUARE
    0x008a: 0x2b1c,     # WHITE LARGE SQUARE
    0x008b: 0x2b1c,     # WHITE LARGE SQUARE
    0x008c: 0x2b1c,     # WHITE LARGE SQUARE
    0x008d: 0x2b1c,     # WHITE LARGE SQUARE
    0x008e: 0x2b1c,     # WHITE LARGE SQUARE
    0x008f: 0x2b1c,     # WHITE LARGE SQUARE
    0x0090: 0x2b1c,     # WHITE LARGE SQUARE
    0x0091: 0x2b1c,     # WHITE LARGE SQUARE
    0x0092: 0x2b1c,     # WHITE LARGE SQUARE
    0x0093: 0x2b1c,     # WHITE LARGE SQUARE
    0x0094: 0x2b1c,     # WHITE LARGE SQUARE
    0x0095: 0x2b1c,     # WHITE LARGE SQUARE
    0x0096: 0x2b1c,     # WHITE LARGE SQUARE
    0x0097: 0x2b1c,     # WHITE LARGE SQUARE
    0x0098: 0x2b1c,     # WHITE LARGE SQUARE
    0x0099: 0x2b1c,     # WHITE LARGE SQUARE
    0x009a: 0x2b1c,     # WHITE LARGE SQUARE
    0x009b: 0x2b1c,     # WHITE LARGE SQUARE
    0x009c: 0x2b1c,     # WHITE LARGE SQUARE
    0x009d: 0x2b1c,     # WHITE LARGE SQUARE
    0x009e: 0x2b1c,     # WHITE LARGE SQUARE
    0x009f: 0x2b1c,     # WHITE LARGE SQUARE
    0x00af: 0x2594,     # UPPER ONE EIGHTH BLOCK
})

decoding_table = (
    u'\x00'     # 0x0000 -> NULL
    u'\x01'     # 0x0001 -> START OF HEADING
    u'\x02'     # 0x0002 -> START OF TEXT
    u'\x03'     # 0x0003 -> END OF TEXT
    u'\x04'     # 0x0004 -> END OF TRANSMISSION
    u'\x05'     # 0x0005 -> ENQUIRY
    u'\x06'     # 0x0006 -> ACKNOWLEDGE
    u'\x07'     # 0x0007 -> BELL
    u'\x08'     # 0x0008 -> BACKSPACE
    u'\t'       # 0x0009 -> HORIZONTAL TABULATION
    u'\n'       # 0x000a -> LINE FEED
    u'\x0b'     # 0x000b -> VERTICAL TABULATION
    u'\x0c'     # 0x000c -> FORM FEED
    u'\r'       # 0x000d -> CARRIAGE RETURN
    u'\x0e'     # 0x000e -> SHIFT OUT
    u'\x0f'     # 0x000f -> SHIFT IN
    u'\x10'     # 0x0010 -> DATA LINK ESCAPE
    u'\x11'     # 0x0011 -> DEVICE CONTROL ONE
    u'\x12'     # 0x0012 -> DEVICE CONTROL TWO
    u'\x13'     # 0x0013 -> DEVICE CONTROL THREE
    u'\x14'     # 0x0014 -> DEVICE CONTROL FOUR
    u'\x15'     # 0x0015 -> NEGATIVE ACKNOWLEDGE
    u'\x16'     # 0x0016 -> SYNCHRONOUS IDLE
    u'\x17'     # 0x0017 -> END OF TRANSMISSION BLOCK
    u'\x18'     # 0x0018 -> CANCEL
    u'\x19'     # 0x0019 -> END OF MEDIUM
    u'\x1a'     # 0x001a -> SUBSTITUTE
    u'\x1b'     # 0x001b -> ESCAPE
    u'\x1c'     # 0x001c -> FILE SEPARATOR
    u'\x1d'     # 0x001d -> GROUP SEPARATOR
    u'\x1e'     # 0x001e -> RECORD SEPARATOR
    u'\x1f'     # 0x001f -> UNIT SEPARATOR
    u' '        # 0x0020 -> SPACE
    u'!'        # 0x0021 -> EXCLAMATION MARK
    u'"'        # 0x0022 -> QUOTATION MARK
    u'#'        # 0x0023 -> NUMBER SIGN
    u'$'        # 0x0024 -> DOLLAR SIGN
    u'%'        # 0x0025 -> PERCENT SIGN
    u'&'        # 0x0026 -> AMPERSAND
    u"'"        # 0x0027 -> APOSTROPHE
    u'('        # 0x0028 -> LEFT PARENTHESIS
    u')'        # 0x0029 -> RIGHT PARENTHESIS
    u'*'        # 0x002a -> ASTERISK
    u'+'        # 0x002b -> PLUS SIGN
    u','        # 0x002c -> COMMA
    u'\u2500'   # 0x002d -> BOX DRAWINGS LIGHT HORIZONTAL
    u'.'        # 0x002e -> FULL STOP
    # 0x002f -> BOX DRAWINGS LIGHT DIAGONAL UPPER RIGHT TO LOWER LEFT
    u'\u2571'
    u'0'        # 0x0030 -> DIGIT ZERO
    u'1'        # 0x0031 -> DIGIT ONE
    u'2'        # 0x0032 -> DIGIT TWO
    u'3'        # 0x0033 -> DIGIT THREE
    u'4'        # 0x0034 -> DIGIT FOUR
    u'5'        # 0x0035 -> DIGIT FIVE
    u'6'        # 0x0036 -> DIGIT SIX
    u'7'        # 0x0037 -> DIGIT SEVEN
    u'8'        # 0x0038 -> DIGIT EIGHT
    u'9'        # 0x0039 -> DIGIT NINE
    u':'        # 0x003a -> COLON
    u';'        # 0x003b -> SEMICOLON
    u'<'        # 0x003c -> LESS-THAN SIGN
    u'='        # 0x003d -> EQUALS SIGN
    u'>'        # 0x003e -> GREATER-THAN SIGN
    u'?'        # 0x003f -> QUESTION MARK
    u'@'        # 0x0040 -> COMMERCIAL AT
    u'A'        # 0x0041 -> LATIN CAPITAL LETTER A
    u'B'        # 0x0042 -> LATIN CAPITAL LETTER B
    u'C'        # 0x0043 -> LATIN CAPITAL LETTER C
    u'D'        # 0x0044 -> LATIN CAPITAL LETTER D
    u'E'        # 0x0045 -> LATIN CAPITAL LETTER E
    u'F'        # 0x0046 -> LATIN CAPITAL LETTER F
    u'G'        # 0x0047 -> LATIN CAPITAL LETTER G
    u'H'        # 0x0048 -> LATIN CAPITAL LETTER H
    u'I'        # 0x0049 -> LATIN CAPITAL LETTER I
    u'J'        # 0x004a -> LATIN CAPITAL LETTER J
    u'K'        # 0x004b -> LATIN CAPITAL LETTER K
    u'L'        # 0x004c -> LATIN CAPITAL LETTER L
    u'M'        # 0x004d -> LATIN CAPITAL LETTER M
    u'N'        # 0x004e -> LATIN CAPITAL LETTER N
    u'O'        # 0x004f -> LATIN CAPITAL LETTER O
    u'P'        # 0x0050 -> LATIN CAPITAL LETTER P
    u'Q'        # 0x0051 -> LATIN CAPITAL LETTER Q
    u'R'        # 0x0052 -> LATIN CAPITAL LETTER R
    u'S'        # 0x0053 -> LATIN CAPITAL LETTER S
    u'T'        # 0x0054 -> LATIN CAPITAL LETTER T
    u'U'        # 0x0055 -> LATIN CAPITAL LETTER U
    u'V'        # 0x0056 -> LATIN CAPITAL LETTER V
    u'W'        # 0x0057 -> LATIN CAPITAL LETTER W
    u'\u2573'   # 0x0058 -> BOX DRAWINGS LIGHT DIAGONAL CROSS
    u'Y'        # 0x0059 -> LATIN CAPITAL LETTER Y
    u'Z'        # 0x005a -> LATIN CAPITAL LETTER Z
    u'['        # 0x005b -> LEFT SQUARE BRACKET
    # 0x005c -> BOX DRAWINGS LIGHT DIAGONAL UPPER LEFT TO LOWER RIGHT
    u'\u2572'
    u']'        # 0x005d -> RIGHT SQUARE BRACKET
    u'^'        # 0x005e -> CIRCUMFLEX ACCENT
    u'\u2581'   # 0x005f -> LOWER ONE EIGHTH BLOCK
    u'`'        # 0x0060 -> GRAVE ACCENT
    u'a'        # 0x0061 -> LATIN SMALL LETTER A
    u'b'        # 0x0062 -> LATIN SMALL LETTER B
    u'c'        # 0x0063 -> LATIN SMALL LETTER C
    u'd'        # 0x0064 -> LATIN SMALL LETTER D
    u'e'        # 0x0065 -> LATIN SMALL LETTER E
    u'f'        # 0x0066 -> LATIN SMALL LETTER F
    u'g'        # 0x0067 -> LATIN SMALL LETTER G
    u'h'        # 0x0068 -> LATIN SMALL LETTER H
    u'i'        # 0x0069 -> LATIN SMALL LETTER I
    u'j'        # 0x006a -> LATIN SMALL LETTER J
    u'k'        # 0x006b -> LATIN SMALL LETTER K
    u'l'        # 0x006c -> LATIN SMALL LETTER L
    u'm'        # 0x006d -> LATIN SMALL LETTER M
    u'n'        # 0x006e -> LATIN SMALL LETTER N
    u'o'        # 0x006f -> LATIN SMALL LETTER O
    u'p'        # 0x0070 -> LATIN SMALL LETTER P
    u'q'        # 0x0071 -> LATIN SMALL LETTER Q
    u'r'        # 0x0072 -> LATIN SMALL LETTER R
    u's'        # 0x0073 -> LATIN SMALL LETTER S
    u't'        # 0x0074 -> LATIN SMALL LETTER T
    u'u'        # 0x0075 -> LATIN SMALL LETTER U
    u'v'        # 0x0076 -> LATIN SMALL LETTER V
    u'w'        # 0x0077 -> LATIN SMALL LETTER W
    u'x'        # 0x0078 -> LATIN SMALL LETTER X
    u'y'        # 0x0079 -> LATIN SMALL LETTER Y
    u'z'        # 0x007a -> LATIN SMALL LETTER Z
    u'{'        # 0x007b -> LEFT CURLY BRACKET
    u'\u2502'   # 0x007c -> BOX DRAWINGS LIGHT VERTICAL
    u'}'        # 0x007d -> RIGHT CURLY BRACKET
    u'~'        # 0x007e -> TILDE
    u'\u259e'   # 0x007f -> QUADRANT UPPER RIGHT AND LOWER LEFT
    u'\u2b1c'   # 0x0080 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0081 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0082 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0083 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0084 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0085 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0086 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0087 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0088 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0089 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x008a -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x008b -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x008c -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x008d -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x008e -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x008f -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0090 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0091 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0092 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0093 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0094 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0095 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0096 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0097 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0098 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x0099 -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x009a -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x009b -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x009c -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x009d -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x009e -> WHITE LARGE SQUARE
    u'\u2b1c'   # 0x009f -> WHITE LARGE SQUARE
    u'\xa0'     # 0x00a0 -> NO-BREAK SPACE
    u'\xa1'     # 0x00a1 -> INVERTED EXCLAMATION MARK
    u'\xa2'     # 0x00a2 -> CENT SIGN
    u'\xa3'     # 0x00a3 -> POUND SIGN
    u'\xa4'     # 0x00a4 -> CURRENCY SIGN
    u'\xa5'     # 0x00a5 -> YEN SIGN
    u'\xa6'     # 0x00a6 -> BROKEN BAR
    u'\xa7'     # 0x00a7 -> SECTION SIGN
    u'\xa8'     # 0x00a8 -> DIAERESIS
    u'\xa9'     # 0x00a9 -> COPYRIGHT SIGN
    u'\xaa'     # 0x00aa -> FEMININE ORDINAL INDICATOR
    u'\xab'     # 0x00ab -> LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    u'\xac'     # 0x00ac -> NOT SIGN
    u'\xad'     # 0x00ad -> SOFT HYPHEN
    u'\xae'     # 0x00ae -> REGISTERED SIGN
    u'\xaf'     # 0x00af -> MACRON
    u'\xb0'     # 0x00b0 -> DEGREE SIGN
    u'\xb1'     # 0x00b1 -> PLUS-MINUS SIGN
    u'\xb2'     # 0x00b2 -> SUPERSCRIPT TWO
    u'\xb3'     # 0x00b3 -> SUPERSCRIPT THREE
    u'\xb4'     # 0x00b4 -> ACUTE ACCENT
    u'\xb5'     # 0x00b5 -> MICRO SIGN
    u'\xb6'     # 0x00b6 -> PILCROW SIGN
    u'\xb7'     # 0x00b7 -> MIDDLE DOT
    u'\xb8'     # 0x00b8 -> CEDILLA
    u'\xb9'     # 0x00b9 -> SUPERSCRIPT ONE
    u'\xba'     # 0x00ba -> MASCULINE ORDINAL INDICATOR
    u'\xbb'     # 0x00bb -> RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    u'\xbc'     # 0x00bc -> VULGAR FRACTION ONE QUARTER
    u'\xbd'     # 0x00bd -> VULGAR FRACTION ONE HALF
    u'\xbe'     # 0x00be -> VULGAR FRACTION THREE QUARTERS
    u'\xbf'     # 0x00bf -> INVERTED QUESTION MARK
    u'\xc0'     # 0x00c0 -> LATIN CAPITAL LETTER A WITH GRAVE
    u'\xc1'     # 0x00c1 -> LATIN CAPITAL LETTER A WITH ACUTE
    u'\xc2'     # 0x00c2 -> LATIN CAPITAL LETTER A WITH CIRCUMFLEX
    u'\xc3'     # 0x00c3 -> LATIN CAPITAL LETTER A WITH TILDE
    u'\xc4'     # 0x00c4 -> LATIN CAPITAL LETTER A WITH DIAERESIS
    u'\xc5'     # 0x00c5 -> LATIN CAPITAL LETTER A WITH RING ABOVE
    u'\xc6'     # 0x00c6 -> LATIN CAPITAL LETTER AE
    u'\xc7'     # 0x00c7 -> LATIN CAPITAL LETTER C WITH CEDILLA
    u'\xc8'     # 0x00c8 -> LATIN CAPITAL LETTER E WITH GRAVE
    u'\xc9'     # 0x00c9 -> LATIN CAPITAL LETTER E WITH ACUTE
    u'\xca'     # 0x00ca -> LATIN CAPITAL LETTER E WITH CIRCUMFLEX
    u'\xcb'     # 0x00cb -> LATIN CAPITAL LETTER E WITH DIAERESIS
    u'\xcc'     # 0x00cc -> LATIN CAPITAL LETTER I WITH GRAVE
    u'\xcd'     # 0x00cd -> LATIN CAPITAL LETTER I WITH ACUTE
    u'\xce'     # 0x00ce -> LATIN CAPITAL LETTER I WITH CIRCUMFLEX
    u'\xcf'     # 0x00cf -> LATIN CAPITAL LETTER I WITH DIAERESIS
    u'\xd0'     # 0x00d0 -> LATIN CAPITAL LETTER ETH
    u'\xd1'     # 0x00d1 -> LATIN CAPITAL LETTER N WITH TILDE
    u'\xd2'     # 0x00d2 -> LATIN CAPITAL LETTER O WITH GRAVE
    u'\xd3'     # 0x00d3 -> LATIN CAPITAL LETTER O WITH ACUTE
    u'\xd4'     # 0x00d4 -> LATIN CAPITAL LETTER O WITH CIRCUMFLEX
    u'\xd5'     # 0x00d5 -> LATIN CAPITAL LETTER O WITH TILDE
    u'\xd6'     # 0x00d6 -> LATIN CAPITAL LETTER O WITH DIAERESIS
    u'\xd7'     # 0x00d7 -> MULTIPLICATION SIGN
    u'\xd8'     # 0x00d8 -> LATIN CAPITAL LETTER O WITH STROKE
    u'\xd9'     # 0x00d9 -> LATIN CAPITAL LETTER U WITH GRAVE
    u'\xda'     # 0x00da -> LATIN CAPITAL LETTER U WITH ACUTE
    u'\xdb'     # 0x00db -> LATIN CAPITAL LETTER U WITH CIRCUMFLEX
    u'\xdc'     # 0x00dc -> LATIN CAPITAL LETTER U WITH DIAERESIS
    u'\xdd'     # 0x00dd -> LATIN CAPITAL LETTER Y WITH ACUTE
    u'\xde'     # 0x00de -> LATIN CAPITAL LETTER THORN
    u'\xdf'     # 0x00df -> LATIN SMALL LETTER SHARP S
    u'\xe0'     # 0x00e0 -> LATIN SMALL LETTER A WITH GRAVE
    u'\xe1'     # 0x00e1 -> LATIN SMALL LETTER A WITH ACUTE
    u'\xe2'     # 0x00e2 -> LATIN SMALL LETTER A WITH CIRCUMFLEX
    u'\xe3'     # 0x00e3 -> LATIN SMALL LETTER A WITH TILDE
    u'\xe4'     # 0x00e4 -> LATIN SMALL LETTER A WITH DIAERESIS
    u'\xe5'     # 0x00e5 -> LATIN SMALL LETTER A WITH RING ABOVE
    u'\xe6'     # 0x00e6 -> LATIN SMALL LETTER AE
    u'\xe7'     # 0x00e7 -> LATIN SMALL LETTER C WITH CEDILLA
    u'\xe8'     # 0x00e8 -> LATIN SMALL LETTER E WITH GRAVE
    u'\xe9'     # 0x00e9 -> LATIN SMALL LETTER E WITH ACUTE
    u'\xea'     # 0x00ea -> LATIN SMALL LETTER E WITH CIRCUMFLEX
    u'\xeb'     # 0x00eb -> LATIN SMALL LETTER E WITH DIAERESIS
    u'\xec'     # 0x00ec -> LATIN SMALL LETTER I WITH GRAVE
    u'\xed'     # 0x00ed -> LATIN SMALL LETTER I WITH ACUTE
    u'\xee'     # 0x00ee -> LATIN SMALL LETTER I WITH CIRCUMFLEX
    u'\xef'     # 0x00ef -> LATIN SMALL LETTER I WITH DIAERESIS
    u'\xf0'     # 0x00f0 -> LATIN SMALL LETTER ETH
    u'\xf1'     # 0x00f1 -> LATIN SMALL LETTER N WITH TILDE
    u'\xf2'     # 0x00f2 -> LATIN SMALL LETTER O WITH GRAVE
    u'\xf3'     # 0x00f3 -> LATIN SMALL LETTER O WITH ACUTE
    u'\xf4'     # 0x00f4 -> LATIN SMALL LETTER O WITH CIRCUMFLEX
    u'\xf5'     # 0x00f5 -> LATIN SMALL LETTER O WITH TILDE
    u'\xf6'     # 0x00f6 -> LATIN SMALL LETTER O WITH DIAERESIS
    u'\xf7'     # 0x00f7 -> DIVISION SIGN
    u'\xf8'     # 0x00f8 -> LATIN SMALL LETTER O WITH STROKE
    u'\xf9'     # 0x00f9 -> LATIN SMALL LETTER U WITH GRAVE
    u'\xfa'     # 0x00fa -> LATIN SMALL LETTER U WITH ACUTE
    u'\xfb'     # 0x00fb -> LATIN SMALL LETTER U WITH CIRCUMFLEX
    u'\xfc'     # 0x00fc -> LATIN SMALL LETTER U WITH DIAERESIS
    u'\xfd'     # 0x00fd -> LATIN SMALL LETTER Y WITH ACUTE
    u'\xfe'     # 0x00fe -> LATIN SMALL LETTER THORN
    u'\xff'     # 0x00ff -> LATIN SMALL LETTER Y WITH DIAERESIS
)
