#!/usr/bin/python
#                          _______
#    ____________ _______ _\__   /_________        ___  _____
#   |    _   _   \   _   |   ____\   _    /       |   |/  _  \
#   |    /   /   /   /   |  |     |  /___/    _   |   |   /  /
#   |___/___/   /___/____|________|___   |   |_|  |___|_____/
#           \__/                     |___|
#
#
# (c) 2009-2012 Wijnand Modderman-Lenstra <maze@pyth0n.org>
#               MIT License
#
"""
IBM Codepage 437 to Unicode mapping helper. A utf-8 terminal can be used to
call this script directly with an ANSI art graphic filename as argument, and a
UTF-8 encoded version of that art will be printed to standard out.
"""
__author__ = "Wijnand Modderman-Lenstra"
__copyright__ = "Copyright 2009-2012"
__license__ = 'MIT'
__email__ = 'maze@pyth0n.org'

# CP437 is a tuple of length 256, mapping equivalent unicode
# characters for each CP437 chr(n), where n is index of CP437.
CP437 = (
    u'\u0000', u'\u0001', u'\u0002', u'\u0003', u'\u0004', u'\u0005',
    u'\u0006', u'\u0007', u'\u0008', u'\u0009', u'\u000A', u'\u000B',
    u'\u000C', u'\u000D', u'\u000E', u'\u000F', u'\u0010', u'\u0011',
    u'\u0012', u'\u0013', u'\u0014', u'\u0015', u'\u0016', u'\u0017',
    u'\u0018', u'\u0019', u'\u001A', u'\u001B', u'\u001C', u'\u001D',
    u'\u001E', u'\u001F', u'\u0020', u'\u0021', u'\u0022', u'\u0023',
    u'\u0024', u'\u0025', u'\u0026', u'\u0027', u'\u0028', u'\u0029',
    u'\u002A', u'\u002B', u'\u002C', u'\u002D', u'\u002E', u'\u002F',
    u'\u0030', u'\u0031', u'\u0032', u'\u0033', u'\u0034', u'\u0035',
    u'\u0036', u'\u0037', u'\u0038', u'\u0039', u'\u003A', u'\u003B',
    u'\u003C', u'\u003D', u'\u003E', u'\u003F', u'\u0040', u'\u0041',
    u'\u0042', u'\u0043', u'\u0044', u'\u0045', u'\u0046', u'\u0047',
    u'\u0048', u'\u0049', u'\u004A', u'\u004B', u'\u004C', u'\u004D',
    u'\u004E', u'\u004F', u'\u0050', u'\u0051', u'\u0052', u'\u0053',
    u'\u0054', u'\u0055', u'\u0056', u'\u0057', u'\u0058', u'\u0059',
    u'\u005A', u'\u005B', u'\u005C', u'\u005D', u'\u005E', u'\u005F',
    u'\u0060', u'\u0061', u'\u0062', u'\u0063', u'\u0064', u'\u0065',
    u'\u0066', u'\u0067', u'\u0068', u'\u0069', u'\u006A', u'\u006B',
    u'\u006C', u'\u006D', u'\u006E', u'\u006F', u'\u0070', u'\u0071',
    u'\u0072', u'\u0073', u'\u0074', u'\u0075', u'\u0076', u'\u0077',
    u'\u0078', u'\u0079', u'\u007A', u'\u007B', u'\u007C', u'\u007D',
    u'\u007E', u'\u007F', u'\u00C7', u'\u00FC', u'\u00E9', u'\u00E2',
    u'\u00E4', u'\u00E0', u'\u00E5', u'\u00E7', u'\u00EA', u'\u00EB',
    u'\u00E8', u'\u00EF', u'\u00EE', u'\u00EC', u'\u00C4', u'\u00C5',
    u'\u00C9', u'\u00E6', u'\u00C6', u'\u00F4', u'\u00F6', u'\u00F2',
    u'\u00FB', u'\u00F9', u'\u00FF', u'\u00D6', u'\u00DC', u'\u00A2',
    u'\u00A3', u'\u00A5', u'\u20A7', u'\u0192', u'\u00E1', u'\u00ED',
    u'\u00F3', u'\u00FA', u'\u00F1', u'\u00D1', u'\u00AA', u'\u00BA',
    u'\u00BF', u'\u2310', u'\u00AC', u'\u00BD', u'\u00BC', u'\u00A1',
    u'\u00AB', u'\u00BB', u'\u2591', u'\u2592', u'\u2593', u'\u2502',
    u'\u2524', u'\u2561', u'\u2562', u'\u2556', u'\u2555', u'\u2563',
    u'\u2551', u'\u2557', u'\u255D', u'\u255C', u'\u255B', u'\u2510',
    u'\u2514', u'\u2534', u'\u252C', u'\u251C', u'\u2500', u'\u253C',
    u'\u255E', u'\u255F', u'\u255A', u'\u2554', u'\u2569', u'\u2566',
    u'\u2560', u'\u2550', u'\u256C', u'\u2567', u'\u2568', u'\u2564',
    u'\u2565', u'\u2559', u'\u2558', u'\u2552', u'\u2553', u'\u256B',
    u'\u256A', u'\u2518', u'\u250C', u'\u2588', u'\u2584', u'\u258C',
    u'\u2590', u'\u2580', u'\u03B1', u'\u00DF', u'\u0393', u'\u03C0',
    u'\u03A3', u'\u03C3', u'\u00B5', u'\u03C4', u'\u03A6', u'\u0398',
    u'\u03A9', u'\u03B4', u'\u221E', u'\u03C6', u'\u03B5', u'\u2229',
    u'\u2261', u'\u00B1', u'\u2265', u'\u2264', u'\u2320', u'\u2321',
    u'\u00F7', u'\u2248', u'\u00B0', u'\u2219', u'\u00B7', u'\u221A',
    u'\u207F', u'\u00B2', u'\u25A0', u'\u00A0')

# prepare static table.
# In python 3, str.maketrans() uses a dictionary of exactly this form.
CP437TABLE = dict([(unichr(i), CP437[i]) for i in range(255)])


def from_cp437(text):
    """ Given a bytestring in IBM codepage 437, return a translated
        unicode string suitable for decoding to UTF-8.
    """
    return u''.join([CP437[ord(byte)] for byte in text])


def run():
    """
    encode filepath of command-line argument 1 and display to stdout
    """
    import sys
    if len(sys.argv) < 2:
        sys.stderr.write('%s <file>\n' % (sys.argv[0],))
        sys.exit(1)
    cptext = file(sys.argv[1]).read()
    sys.stdout.write(from_cp437(cptext).encode('utf8'))
    return 0

if __name__ == '__main__':
    exit(run())
