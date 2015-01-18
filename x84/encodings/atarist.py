"""
Atari ST codec for x/84.

Generated from:
ftp://ftp.unicode.org/Public/MAPPINGS/VENDORS/MISC/ATARIST.TXT
"""

import codecs

# Codec APIs


class Codec(codecs.Codec):

    def encode(self, char, errors='strict'):
        return codecs.charmap_encode(char, errors, ENCODING_TABLE)

    def decode(self, char, errors='strict'):
        return codecs.charmap_decode(char, errors, DECODING_TABLE)


class IncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, char, final=False):
        return codecs.charmap_encode(char, self.errors, ENCODING_TABLE)[0]


class IncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, char, final=False):
        return codecs.charmap_decode(char, self.errors, DECODING_TABLE)[0]


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


# encodings module API

def getaliases():
    return ('atari',)


def getregentry():
    return codecs.CodecInfo(
        name='atarist',
        encode=Codec().encode,
        decode=Codec().decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


# Decoding Table

DECODING_TABLE = (
    u'\x00'  # 0x00 -> NULL
    u'\x01'  # 0x01 -> START OF HEADING
    u'\x02'  # 0x02 -> START OF TEXT
    u'\x03'  # 0x03 -> END OF TEXT
    u'\x04'  # 0x04 -> END OF TRANSMISSION
    u'\x05'  # 0x05 -> ENQUIRY
    u'\x06'  # 0x06 -> ACKNOWLEDGE
    u'\x07'  # 0x07 -> BELL
    u'\x08'  # 0x08 -> BACKSPACE
    u'\t'  # 0x09 -> HORIZONTAL TABULATION
    u'\n'  # 0x0A -> LINE FEED
    u'\x0b'  # 0x0B -> VERTICAL TABULATION
    u'\x0c'  # 0x0C -> FORM FEED
    u'\r'  # 0x0D -> CARRIAGE RETURN
    u'\x0e'  # 0x0E -> SHIFT OUT
    u'\x0f'  # 0x0F -> SHIFT IN
    u'\x10'  # 0x10 -> DATA LINK ESCAPE
    u'\x11'  # 0x11 -> DEVICE CONTROL ONE
    u'\x12'  # 0x12 -> DEVICE CONTROL TWO
    u'\x13'  # 0x13 -> DEVICE CONTROL THREE
    u'\x14'  # 0x14 -> DEVICE CONTROL FOUR
    u'\x15'  # 0x15 -> NEGATIVE ACKNOWLEDGE
    u'\x16'  # 0x16 -> SYNCHRONOUS IDLE
    u'\x17'  # 0x17 -> END OF TRANSMISSION BLOCK
    u'\x18'  # 0x18 -> CANCEL
    u'\x19'  # 0x19 -> END OF MEDIUM
    u'\x1a'  # 0x1A -> SUBSTITUTE
    u'\x1b'  # 0x1B -> ESCAPE
    u'\x1c'  # 0x1C -> FILE SEPARATOR
    u'\x1d'  # 0x1D -> GROUP SEPARATOR
    u'\x1e'  # 0x1E -> RECORD SEPARATOR
    u'\x1f'  # 0x1F -> UNIT SEPARATOR
    u' '  # 0x20 -> SPACE
    u'!'  # 0x21 -> EXCLAMATION MARK
    u'"'  # 0x22 -> QUOTATION MARK
    u'#'  # 0x23 -> NUMBER SIGN
    u'$'  # 0x24 -> DOLLAR SIGN
    u'%'  # 0x25 -> PERCENT SIGN
    u'&'  # 0x26 -> AMPERSAND
    u"'"  # 0x27 -> APOSTROPHE
    u'('  # 0x28 -> LEFT PARENTHESIS
    u')'  # 0x29 -> RIGHT PARENTHESIS
    u'*'  # 0x2A -> ASTERISK
    u'+'  # 0x2B -> PLUS SIGN
    u','  # 0x2C -> COMMA
    u'-'  # 0x2D -> HYPHEN-MINUS
    u'.'  # 0x2E -> FULL STOP
    u'/'  # 0x2F -> SOLIDUS
    u'0'  # 0x30 -> DIGIT ZERO
    u'1'  # 0x31 -> DIGIT ONE
    u'2'  # 0x32 -> DIGIT TWO
    u'3'  # 0x33 -> DIGIT THREE
    u'4'  # 0x34 -> DIGIT FOUR
    u'5'  # 0x35 -> DIGIT FIVE
    u'6'  # 0x36 -> DIGIT SIX
    u'7'  # 0x37 -> DIGIT SEVEN
    u'8'  # 0x38 -> DIGIT EIGHT
    u'9'  # 0x39 -> DIGIT NINE
    u':'  # 0x3A -> COLON
    u';'  # 0x3B -> SEMICOLON
    u'<'  # 0x3C -> LESS-THAN SIGN
    u'='  # 0x3D -> EQUALS SIGN
    u'>'  # 0x3E -> GREATER-THAN SIGN
    u'?'  # 0x3F -> QUESTION MARK
    u'@'  # 0x40 -> COMMERCIAL AT
    u'A'  # 0x41 -> LATIN CAPITAL LETTER A
    u'B'  # 0x42 -> LATIN CAPITAL LETTER B
    u'C'  # 0x43 -> LATIN CAPITAL LETTER C
    u'D'  # 0x44 -> LATIN CAPITAL LETTER D
    u'E'  # 0x45 -> LATIN CAPITAL LETTER E
    u'F'  # 0x46 -> LATIN CAPITAL LETTER F
    u'G'  # 0x47 -> LATIN CAPITAL LETTER G
    u'H'  # 0x48 -> LATIN CAPITAL LETTER H
    u'I'  # 0x49 -> LATIN CAPITAL LETTER I
    u'J'  # 0x4A -> LATIN CAPITAL LETTER J
    u'K'  # 0x4B -> LATIN CAPITAL LETTER K
    u'L'  # 0x4C -> LATIN CAPITAL LETTER L
    u'M'  # 0x4D -> LATIN CAPITAL LETTER M
    u'N'  # 0x4E -> LATIN CAPITAL LETTER N
    u'O'  # 0x4F -> LATIN CAPITAL LETTER O
    u'P'  # 0x50 -> LATIN CAPITAL LETTER P
    u'Q'  # 0x51 -> LATIN CAPITAL LETTER Q
    u'R'  # 0x52 -> LATIN CAPITAL LETTER R
    u'S'  # 0x53 -> LATIN CAPITAL LETTER S
    u'T'  # 0x54 -> LATIN CAPITAL LETTER T
    u'U'  # 0x55 -> LATIN CAPITAL LETTER U
    u'V'  # 0x56 -> LATIN CAPITAL LETTER V
    u'W'  # 0x57 -> LATIN CAPITAL LETTER W
    u'X'  # 0x58 -> LATIN CAPITAL LETTER X
    u'Y'  # 0x59 -> LATIN CAPITAL LETTER Y
    u'Z'  # 0x5A -> LATIN CAPITAL LETTER Z
    u'['  # 0x5B -> LEFT SQUARE BRACKET
    u'\\'  # 0x5C -> REVERSE SOLIDUS
    u']'  # 0x5D -> RIGHT SQUARE BRACKET
    u'^'  # 0x5E -> CIRCUMFLEX ACCENT
    u'_'  # 0x5F -> LOW LINE
    u'`'  # 0x60 -> GRAVE ACCENT
    u'a'  # 0x61 -> LATIN SMALL LETTER A
    u'b'  # 0x62 -> LATIN SMALL LETTER B
    u'c'  # 0x63 -> LATIN SMALL LETTER C
    u'd'  # 0x64 -> LATIN SMALL LETTER D
    u'e'  # 0x65 -> LATIN SMALL LETTER E
    u'f'  # 0x66 -> LATIN SMALL LETTER F
    u'g'  # 0x67 -> LATIN SMALL LETTER G
    u'h'  # 0x68 -> LATIN SMALL LETTER H
    u'i'  # 0x69 -> LATIN SMALL LETTER I
    u'j'  # 0x6A -> LATIN SMALL LETTER J
    u'k'  # 0x6B -> LATIN SMALL LETTER K
    u'l'  # 0x6C -> LATIN SMALL LETTER L
    u'm'  # 0x6D -> LATIN SMALL LETTER M
    u'n'  # 0x6E -> LATIN SMALL LETTER N
    u'o'  # 0x6F -> LATIN SMALL LETTER O
    u'p'  # 0x70 -> LATIN SMALL LETTER P
    u'q'  # 0x71 -> LATIN SMALL LETTER Q
    u'r'  # 0x72 -> LATIN SMALL LETTER R
    u's'  # 0x73 -> LATIN SMALL LETTER S
    u't'  # 0x74 -> LATIN SMALL LETTER T
    u'u'  # 0x75 -> LATIN SMALL LETTER U
    u'v'  # 0x76 -> LATIN SMALL LETTER V
    u'w'  # 0x77 -> LATIN SMALL LETTER W
    u'x'  # 0x78 -> LATIN SMALL LETTER X
    u'y'  # 0x79 -> LATIN SMALL LETTER Y
    u'z'  # 0x7A -> LATIN SMALL LETTER Z
    u'{'  # 0x7B -> LEFT CURLY BRACKET
    u'|'  # 0x7C -> VERTICAL LINE
    u'}'  # 0x7D -> RIGHT CURLY BRACKET
    u'~'  # 0x7E -> TILDE
    u'\x7f'  # 0x7F -> DELETE
    u'\xc7'  # 0x80 -> LATIN CAPITAL LETTER C WITH CEDILLA
    u'\xfc'  # 0x81 -> LATIN SMALL LETTER U WITH DIAERESIS
    u'\xe9'  # 0x82 -> LATIN SMALL LETTER E WITH ACUTE
    u'\xe2'  # 0x83 -> LATIN SMALL LETTER A WITH CIRCUMFLEX
    u'\xe4'  # 0x84 -> LATIN SMALL LETTER A WITH DIAERESIS
    u'\xe0'  # 0x85 -> LATIN SMALL LETTER A WITH GRAVE
    u'\xe5'  # 0x86 -> LATIN SMALL LETTER A WITH RING ABOVE
    u'\xe7'  # 0x87 -> LATIN SMALL LETTER C WITH CEDILLA
    u'\xea'  # 0x88 -> LATIN SMALL LETTER E WITH CIRCUMFLEX
    u'\xeb'  # 0x89 -> LATIN SMALL LETTER E WITH DIAERESIS
    u'\xe8'  # 0x8A -> LATIN SMALL LETTER E WITH GRAVE
    u'\xef'  # 0x8B -> LATIN SMALL LETTER I WITH DIAERESIS
    u'\xee'  # 0x8C -> LATIN SMALL LETTER I WITH CIRCUMFLEX
    u'\xec'  # 0x8D -> LATIN SMALL LETTER I WITH GRAVE
    u'\xc4'  # 0x8E -> LATIN CAPITAL LETTER A WITH DIAERESIS
    u'\xc5'  # 0x8F -> LATIN CAPITAL LETTER A WITH RING ABOVE
    u'\xc9'  # 0x90 -> LATIN CAPITAL LETTER E WITH ACUTE
    u'\xe6'  # 0x91 -> LATIN SMALL LETTER AE
    u'\xc6'  # 0x92 -> LATIN CAPITAL LETTER AE
    u'\xf4'  # 0x93 -> LATIN SMALL LETTER O WITH CIRCUMFLEX
    u'\xf6'  # 0x94 -> LATIN SMALL LETTER O WITH DIAERESIS
    u'\xf2'  # 0x95 -> LATIN SMALL LETTER O WITH GRAVE
    u'\xfb'  # 0x96 -> LATIN SMALL LETTER U WITH CIRCUMFLEX
    u'\xf9'  # 0x97 -> LATIN SMALL LETTER U WITH GRAVE
    u'\xff'  # 0x98 -> LATIN SMALL LETTER Y WITH DIAERESIS
    u'\xd6'  # 0x99 -> LATIN CAPITAL LETTER O WITH DIAERESIS
    u'\xdc'  # 0x9A -> LATIN CAPITAL LETTER U WITH DIAERESIS
    u'\xa2'  # 0x9B -> CENT SIGN
    u'\xa3'  # 0x9C -> POUND SIGN
    u'\xa5'  # 0x9D -> YEN SIGN
    u'\xdf'  # 0x9E -> LATIN SMALL LETTER SHARP S
    u'\u0192'  # 0x9F -> LATIN SMALL LETTER F WITH HOOK
    u'\xe1'  # 0xA0 -> LATIN SMALL LETTER A WITH ACUTE
    u'\xed'  # 0xA1 -> LATIN SMALL LETTER I WITH ACUTE
    u'\xf3'  # 0xA2 -> LATIN SMALL LETTER O WITH ACUTE
    u'\xfa'  # 0xA3 -> LATIN SMALL LETTER U WITH ACUTE
    u'\xf1'  # 0xA4 -> LATIN SMALL LETTER N WITH TILDE
    u'\xd1'  # 0xA5 -> LATIN CAPITAL LETTER N WITH TILDE
    u'\xaa'  # 0xA6 -> FEMININE ORDINAL INDICATOR
    u'\xba'  # 0xA7 -> MASCULINE ORDINAL INDICATOR
    u'\xbf'  # 0xA8 -> INVERTED QUESTION MARK
    u'\u2310'  # 0xA9 -> REVERSED NOT SIGN
    u'\xac'  # 0xAA -> NOT SIGN
    u'\xbd'  # 0xAB -> VULGAR FRACTION ONE HALF
    u'\xbc'  # 0xAC -> VULGAR FRACTION ONE QUARTER
    u'\xa1'  # 0xAD -> INVERTED EXCLAMATION MARK
    u'\xab'  # 0xAE -> LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    u'\xbb'  # 0xAF -> RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    u'\xe3'  # 0xB0 -> LATIN SMALL LETTER A WITH TILDE
    u'\xf5'  # 0xB1 -> LATIN SMALL LETTER O WITH TILDE
    u'\xd8'  # 0xB2 -> LATIN CAPITAL LETTER O WITH STROKE
    u'\xf8'  # 0xB3 -> LATIN SMALL LETTER O WITH STROKE
    u'\u0153'  # 0xB4 -> LATIN SMALL LIGATURE OE
    u'\u0152'  # 0xB5 -> LATIN CAPITAL LIGATURE OE
    u'\xc0'  # 0xB6 -> LATIN CAPITAL LETTER A WITH GRAVE
    u'\xc3'  # 0xB7 -> LATIN CAPITAL LETTER A WITH TILDE
    u'\xd5'  # 0xB8 -> LATIN CAPITAL LETTER O WITH TILDE
    u'\xa8'  # 0xB9 -> DIAERESIS
    u'\xb4'  # 0xBA -> ACUTE ACCENT
    u'\u2020'  # 0xBB -> DAGGER
    u'\xb6'  # 0xBC -> PILCROW SIGN
    u'\xa9'  # 0xBD -> COPYRIGHT SIGN
    u'\xae'  # 0xBE -> REGISTERED SIGN
    u'\u2122'  # 0xBF -> TRADE MARK SIGN
    u'\u0133'  # 0xC0 -> LATIN SMALL LIGATURE IJ
    u'\u0132'  # 0xC1 -> LATIN CAPITAL LIGATURE IJ
    u'\u05d0'  # 0xC2 -> HEBREW LETTER ALEF
    u'\u05d1'  # 0xC3 -> HEBREW LETTER BET
    u'\u05d2'  # 0xC4 -> HEBREW LETTER GIMEL
    u'\u05d3'  # 0xC5 -> HEBREW LETTER DALET
    u'\u05d4'  # 0xC6 -> HEBREW LETTER HE
    u'\u05d5'  # 0xC7 -> HEBREW LETTER VAV
    u'\u05d6'  # 0xC8 -> HEBREW LETTER ZAYIN
    u'\u05d7'  # 0xC9 -> HEBREW LETTER HET
    u'\u05d8'  # 0xCA -> HEBREW LETTER TET
    u'\u05d9'  # 0xCB -> HEBREW LETTER YOD
    u'\u05db'  # 0xCC -> HEBREW LETTER KAF
    u'\u05dc'  # 0xCD -> HEBREW LETTER LAMED
    u'\u05de'  # 0xCE -> HEBREW LETTER MEM
    u'\u05e0'  # 0xCF -> HEBREW LETTER NUN
    u'\u05e1'  # 0xD0 -> HEBREW LETTER SAMEKH
    u'\u05e2'  # 0xD1 -> HEBREW LETTER AYIN
    u'\u05e4'  # 0xD2 -> HEBREW LETTER PE
    u'\u05e6'  # 0xD3 -> HEBREW LETTER TSADI
    u'\u05e7'  # 0xD4 -> HEBREW LETTER QOF
    u'\u05e8'  # 0xD5 -> HEBREW LETTER RESH
    u'\u05e9'  # 0xD6 -> HEBREW LETTER SHIN
    u'\u05ea'  # 0xD7 -> HEBREW LETTER TAV
    u'\u05df'  # 0xD8 -> HEBREW LETTER FINAL NUN
    u'\u05da'  # 0xD9 -> HEBREW LETTER FINAL KAF
    u'\u05dd'  # 0xDA -> HEBREW LETTER FINAL MEM
    u'\u05e3'  # 0xDB -> HEBREW LETTER FINAL PE
    u'\u05e5'  # 0xDC -> HEBREW LETTER FINAL TSADI
    u'\xa7'  # 0xDD -> SECTION SIGN
    u'\u2227'  # 0xDE -> LOGICAL AND
    u'\u221e'  # 0xDF -> INFINITY
    u'\u03b1'  # 0xE0 -> GREEK SMALL LETTER ALPHA
    u'\u03b2'  # 0xE1 -> GREEK SMALL LETTER BETA
    u'\u0393'  # 0xE2 -> GREEK CAPITAL LETTER GAMMA
    u'\u03c0'  # 0xE3 -> GREEK SMALL LETTER PI
    u'\u03a3'  # 0xE4 -> GREEK CAPITAL LETTER SIGMA
    u'\u03c3'  # 0xE5 -> GREEK SMALL LETTER SIGMA
    u'\xb5'  # 0xE6 -> MICRO SIGN
    u'\u03c4'  # 0xE7 -> GREEK SMALL LETTER TAU
    u'\u03a6'  # 0xE8 -> GREEK CAPITAL LETTER PHI
    u'\u0398'  # 0xE9 -> GREEK CAPITAL LETTER THETA
    u'\u03a9'  # 0xEA -> GREEK CAPITAL LETTER OMEGA
    u'\u03b4'  # 0xEB -> GREEK SMALL LETTER DELTA
    u'\u222e'  # 0xEC -> CONTOUR INTEGRAL
    u'\u03c6'  # 0xED -> GREEK SMALL LETTER PHI
    u'\u2208'  # 0xEE -> ELEMENT OF SIGN
    u'\u2229'  # 0xEF -> INTERSECTION
    u'\u2261'  # 0xF0 -> IDENTICAL TO
    u'\xb1'  # 0xF1 -> PLUS-MINUS SIGN
    u'\u2265'  # 0xF2 -> GREATER-THAN OR EQUAL TO
    u'\u2264'  # 0xF3 -> LESS-THAN OR EQUAL TO
    u'\u2320'  # 0xF4 -> TOP HALF INTEGRAL
    u'\u2321'  # 0xF5 -> BOTTOM HALF INTEGRAL
    u'\xf7'  # 0xF6 -> DIVISION SIGN
    u'\u2248'  # 0xF7 -> ALMOST EQUAL TO
    u'\xb0'  # 0xF8 -> DEGREE SIGN
    u'\u2219'  # 0xF9 -> BULLET OPERATOR
    u'\xb7'  # 0xFA -> MIDDLE DOT
    u'\u221a'  # 0xFB -> SQUARE ROOT
    u'\u207f'  # 0xFC -> SUPERSCRIPT LATIN SMALL LETTER N
    u'\xb2'  # 0xFD -> SUPERSCRIPT TWO
    u'\xb3'  # 0xFE -> SUPERSCRIPT THREE
    u'\xaf'  # 0xFF -> MACRON
)

# Encoding table
ENCODING_TABLE = codecs.charmap_build(DECODING_TABLE)
