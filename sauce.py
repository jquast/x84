#! /usr/bin/env python
# 
#     _____         ____                            _______
#  __|     |_______|__  |____ ____________ _______ _\__   /_________
#  \_       _/  _    /       |    _   _   \   _   |   ____\   _    /
#    |     |    /___/   _    |    /   /   /   /   |  |     |  /___/
#    |     |____    |___/____|___/___/   /___/____|________|___   |  .COM
#    |_____|    |___|                \__/                     |___|
#  
#
# (c) 2006, 2009 Wijnand 'tehmaze' Modderman - http://tehmaze.com
#

'''
Parser for SAUCE or Standard Architecture for Universal Comment Extensions.
$Id: sauce.py,v 1.9 2009/05/21 13:38:08 maze Exp $
'''

__author__    = 'Wijnand Modderman <python@tehmaze.com>'
__copyright__ = '(C) 2006, 2009 Wijnand Modderman'
__license__   = 'LGPL'
__version__   = '0.1'
__url__       = 'http://dev.tehmaze.com/code/'

import datetime
import os
import struct
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class SAUCE(object):
    '''
    Parser for SAUCE or Standard Architecture for Universal Comment Extensions,
    as defined in http://www.acid.org/info/sauce/s_spec.htm.

    :param filename:    file name or file handle
    :property author:   Name or 'handle' of the creator of the file
    :property datatype: Type of data
    :property date:     Date the file was created
    :property filesize: Original filesize NOT including any information of SAUCE
    :property group:    Name of the group/company the creator is employed by
    :property title:    Title of the file

    Example::

        >>> art = open('31337.ANS', 'rb')
        >>> nfo = sauce.SAUCE(art)
        >>> nfo.author
        'maze'
        ...
        >>> nfo.group
        ''
        >>> nfo.group = 'mononoke'
        >>> raw = str(nfo)

    Saving the new file::

        >>> sav = open('31337.NEW', 'wb')
        >>> nfo.write(sav)
        >>> # OR you can do:
        >>> sav = nfo.write('31337.NEW')

    '''

    # template
    template  = (
                    # name           default       size type
                    ('SAUCE',        'SAUCE',      5,   '5s'),
                    ('SAUCEVersion', '00',         2,   '2s'),
                    ('Title',        '\x00' * 35, 35,   '35s'),
                    ('Author',       '\x00' * 20, 20,   '20s'),
                    ('Group',        '\x00' * 20, 20,   '20s'),
                    ('Date',         '\x00' * 8,   8,   '8s'),
                    ('FileSize',     [0],          4,   'I'),
                    ('DataType',     [0],          1,   'B'),
                    ('FileType',     [0],          1,   'B'),
                    ('TInfo1',       [0],          1,   'H'),
                    ('TInfo2',       [0],          1,   'H'),
                    ('TInfo3',       [0],          1,   'H'),
                    ('TInfo4',       [0],          1,   'H'),
                    ('Comments',     [0],          1,   'B'),
                    ('Flags',        [0],          1,   'B'),
                    ('Filler',       ['\x00']*22, 22,   '22c'),
    )
    templates = [t[0] for t in template]
    datatypes = ['None', 'Character', 'Graphics', 'Vector', 'Sound',
                 'BinaryText', 'XBin', 'Archive', 'Executable']
    filetypes = {
            'None': {
                'filetype': ['Undefined'],
            },
            'Character': {
                'filetype': ['ASCII', 'ANSi', 'ANSiMation', 'RIP', 'PCBoard', 
                             'Avatar', 'HTML', 'Source'],
                'flags':    {0: 'None', 1: 'iCE Color'},
                'tinfo': (
                    ('width', 'height',     None, None),
                    ('width', 'height',     None, None),
                    ('width', 'height',     None, None),
                    ('width', 'height', 'colors', None),
                    ('width', 'height',     None, None),
                    ('width', 'height',     None, None),
                    (   None,     None,     None, None),
                ),
            },
            'Graphics': {
                'filetype': ['GIF', 'PCX', 'LBM/IFF', 'TGA', 'FLI', 'FLC', 
                             'BMP', 'GL', 'DL', 'WPG', 'PNG', 'JPG', 'MPG', 
                             'AVI'],
                'tinfo':    (('width', 'height', 'bpp')) * 14,
            },
            'Vector': {
                'filetype': ['DX', 'DWG', 'WPG', '3DS'],
            },
            'Sound': {
                'filetype': ['MOD', '669', 'STM', 'S3M', 'MTM', 'FAR', 'ULT', 
                             'AMF', 'DMF', 'OKT', 'ROL', 'CMF', 'MIDI', 'SADT',
                             'VOC', 'WAV', 'SMP8', 'SMP8S', 'SMP16', 'SMP16S',
                             'PATCH8', 'PATCH16', 'XM', 'HSC', 'IT'],
                'tinfo':    ((None,)) * 16 + (('Sampling Rate',)) * 4,
            },
            'BinaryText': {
                'flags':    {0: 'None', 1: 'iCE Color'},
            },
            'XBin': {
                'tinfo':    (('width', 'height'),),
            },
            'Archive': {
                'filetype': ['ZIP', 'ARJ', 'LZH', 'ARC', 'TAR', 'ZOO', 'RAR', 
                             'UC2', 'PAK', 'SQZ'],
            },
        }

    def __init__(self, filename='', data=''):
        assert (filename or data), 'Need either filename or record'

        if filename:
            if type(filename) == file:
                self.filehand = filename
            else:
                self.filehand = open(filename, 'rb')
            self._size = os.path.getsize(self.filehand.name)
        else:
            self._size = len(data)
            self.filehand = StringIO(data)

        self.record = self._read()

    def __str__(self):
        return ''.join(list(self._read_file()))

    def _read_file(self):
        # Buffered reader (generator), reads the original file without SAUCE 
        # record.
        self.filehand.seek(0)
        # Check if we have SAUCE data
        if self.record:
            reads, rest = divmod(self._size - 128, 1024)
        else:
            reads, rest = divmod(self._size, 1024)
        for x in xrange(0, reads):
            yield self.filehand.read(1024)
        if rest:
            yield self.filehand.read(rest)

    def _read(self):
        if self._size >= 128:
            self.filehand.seek(self._size - 128)
            record = self.filehand.read(128)
            if record.startswith('SAUCE'):
                return record
        return None

    def _gets(self, key):
        name, default, offset, size, stype = self._template(key)
        data = self.record[offset:offset+size]
        data = struct.unpack(stype, data)
        if stype[-1] in 'cs':
            return ''.join(data)
        elif stype[-1] in 'BI' and len(stype) == 1:
            return data[0]
        else:
            return data

    def _puts(self, key, data):
        name, default, offset, size, stype = self._template(key)
        print offset, size, data, repr(struct.pack(stype, data))
        if self.record is None:
            self.record = self.sauce()
        self.record = ''.join([
            self.record[:offset],
            struct.pack(stype, data),
            self.record[offset+size:]
        ])
        return self.record

    def _template(self, key):
        index = self.templates.index(key)
        name, default, size, stype = self.template[index]
        offset = sum([self.template[x][2] for x in xrange(0, index)])
        return name, default, offset, size, stype

    def sauce(self):
        '''
        Get the raw SAUCE record.
        '''
        if self.record:
            return self.record
        else:
            data = 'SAUCE'
            for name, default, size, stype in self.template[1:]:
                print stype, default
                if stype[-1] in 's':
                    data += struct.pack(stype, default)
                else:
                    data += struct.pack(stype, *default)
            return data


    def write(self, filename):
        '''
        Save the file including SAUCE data to the given file(handle).
        '''
        filename = type(filename) == file and filename or open(filename, 'wb')
        for part in self._read_file():
            filename.write(part)
        filename.write(self.sauce())
        return filename

    # SAUCE meta data

    def get_author(self):
        return self._gets('Author').strip()

    def set_author(self, author):
        self._puts('Author', author)

    def get_datatype(self):
        return self._gets('DataType')

    def get_datatype_str(self):
        datatype = self.datatype
        if datatype <= len(self.datatypes):
            return self.datatypes[datatype]
        else:
            return None

    def set_datatype(self, datatype):
        if type(datatype) == str:
            datatype = datatype.lower().title() # fOoBAR -> Foobar
            datatype = self.recordtypes.index(datatype)
        self._puts('DataType', datatype)

    def get_date(self):
        return self._gets('Date')

    def get_date_str(self, format='%Y%m%d'):
        return datetime.datetime.strptime(self.date, format)

    def set_date(self, date=None, format='%Y%m%d'):
        if date is None:
            date = datetime.datetime.now().strftime(format)
        elif type(date) in [datetime.date, datetime.datetime]:
            date = date.strftime(format)
        elif type(date) in [int, long, float]:
            date = datetime.datetime.fromtimestamp(date).strftime(format)
        self._puts('Date', date)

    def get_filesize(self):
        return self._gets('FileSize')

    def set_filesize(self, size):
        self._puts('FileSize', size)

    def get_filetype(self):
        datatype = self.datatype
        filetype = self._gets('FileType')

    def get_filetype_str(self):
        datatype = self.datatype_str
        filetype = self.filetype

        if datatype is None or filetype is None:
            return None

        if datatype in self.filetypes and \
            'filetype' in self.filetypes[datatype] and \
            filetype <= len(self.filetypes[datatype]['filetype']):
            return self.filetypes[datatype]['filetype'][filetype]
        else:
            return None

    def set_filetype(self, filetype):
        self._puts('FileType', filetype)

    def get_flags(self):
        return self._gets('Flags')

    def set_flags(self, flags):
        self._puts('Flags', flags)

    def get_flags_str(self):
        datatype = self.datatype_str
        filetype = self.filetype

        if datatype is None or filetype is None:
            return None

        if datatype in self.filetypes and \
            'flags' in self.filetypes[datatype] and \
            filetype <= len(self.filetypes[datatype]['filetype']):
            return self.filetypes[datatype]['filetype'][filetype]
        else:
            return None

    def get_group(self):
        return self._gets('Group').strip()

    def set_group(self, group):
        self._puts('Group', group)

    def get_title(self):
        return self._gets('Title').strip()

    def set_title(self, title):
        self._puts('Title', title)

    def get_version(self):
        return self._gets('SAUCEVersion')

    def set_version(self, version):
        self._puts('SAUCEVersion', version)

    # properties
    author       = property(get_author,   set_author)
    datatype     = property(get_datatype, set_datatype)
    datatype_str = property(get_datatype_str)
    date         = property(get_date,     set_date)
    filesize     = property(get_filesize, set_filesize)
    filetype     = property(get_filetype, set_filetype)
    filetype_str = property(get_filetype_str)
    flags        = property(get_flags,    set_flags)
    flags_str    = property(get_flags_str)
    group        = property(get_group,    set_group)
    title        = property(get_title,    set_title)
    version      = property(get_version)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print >>sys.stderr, '%s <file>' % (sys.argv[0],)
        sys.exit(1)
    else:
        test = SAUCE(sys.argv[1])

        def show(sauce):
            print 'Version.:', sauce.version
            print 'Title...:', sauce.title
            print 'Author..:', sauce.author
            print 'Group...:', sauce.group
            print 'Date....:', sauce.date
            print 'FileSize:', sauce.filesize
            print 'DataType:', sauce.datatype, sauce.datatype_str
            print 'FileType:', sauce.filetype, sauce.filetype_str
            print 'Flags...:', sauce.flags, sauce.flags_str
            print 'Record..:', len(sauce.record), repr(sauce.record)

        if test.record:
            show(test)
        else:
            print 'No SAUCE record found'
            test = SAUCE(data=test.sauce())
            show(test)

