""" File browsing/flagging for x/84 bbs https://github.com/jquast/x84 """
# std imports
from __future__ import division
import zipfile
import os

# local
from x84.bbs import getsession, getterminal, echo, getch, syncterm_setfont
from x84.bbs import get_ini, DBProxy, Lightbar, LineEditor
from x84.bbs import send_modem, recv_modem
from x84.default.common import filesize

#: file description database
DIZ_DB = 'filediz'

#: color used for menu key entries
color_highlight = get_ini(
    section='fbrowse', key='color_highlight'
) or 'white_on_blue'

#: color used for borders
color_border = get_ini(
    section='fbrowse', key='color_border',
) or 'bold_blue'

#: fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='fbrowse', key='syncterm_font'
) or 'cp437'

#: marker for flagged files in browser list
flagged_char = get_ini(
    section='fbrowse', key='flagged_char'
) or u'+'

#: extensions for ASCII collies
colly_extensions = get_ini(
    section='fbrowse', key='colly_extensions', split=True
) or ['txt', 'asc', 'ans']

#: author describes as "dirname for flagged listing"
flagged_dirname = get_ini(
    section='fbrowse', key='flagged_dirname'
) or u'__flagged__/'

#: decoding to use for ASCII collies
colly_decoding = get_ini(
    section='fbrowse', key='colly_decoding'
) or 'amiga'


def diz_from_zip(filename, method=zipfile.ZIP_STORED):
    """
    unzip `filename` using particular zipfile `method`
    supports zip, bz2, bzip2; decodes FILE_ID.DIZ as cp437_art
    """

    try:
        myzip = zipfile.ZipFile(filename, compression=method, allowZip64=True)
        for cname in (cname for cname in myzip.namelist()
                      if cname.lower() == 'file_id.diz'):
            return myzip.read(cname).decode('cp437_art')
        return u'No description'
    except zipfile.BadZipfile:
        return u'Bad zip file, cannot parse'
    except zipfile.LargeZipFile:
        # since we do allowZip64=True above, this shouldn't happen any longer
        return u'Large zip file, cannot parse'
    except NotImplementedError:
        return u'Unsupported compression, cannot parse'


def get_diz_from_colly(session, filepath):
    colly = open(filepath, 'r').read()
    colly_diz_begin = '@BEGIN_FILE_ID.DIZ '
    colly_diz_end = '@END_FILE_ID.DIZ'
    pos = colly.find(colly_diz_begin)
    if pos > 0:
        colly = colly[pos + len(colly_diz_begin):]
        pos = colly.find(colly_diz_end)
        if pos > 0:
            decoder = (colly_decoding if session.encoding == 'utf8'
                       else 'cp437_art')
            return colly[:pos].decode(decoder).splitlines()
    return None


def get_instructions(term):
    return [
        term.bold_blue_underline(u'Instructions'),
        u' ',
        u'{0} Un/flag file for download'
        .format(term.reverse(u'(SPACE)')),
        u'{0}  Back up'
        .format(term.reverse(u'(LEFT)')),
        term.reverse(u'(RIGHT, ENTER)'),
        u'        Browse subdirectory',
        u'{0}     Download flagged file(s)'
        .format(term.reverse(u'(D)')),
        u'{0}     Unflag all files'
        .format(term.reverse(u'(-)')),
        u'{0}     Upload file(s)'
        .format(term.reverse(u'(U)')),
        u'{0}     Quit'
        .format(term.reverse(u'(Q)')),
        u' ',
        u'Files are also available via {0}'
        .format(term.bold(u'SFTP')),
    ]


def decode_colly(session, diz_data, extension):
    if (extension in colly_extensions and
            session.encoding == 'utf8'):
        return [line.encode('cp437').decode(colly_decoding)
                for line in diz_data]
    return diz_data


DIZ_EXTRACTORS = {
    'zip': diz_from_zip,
    # DISABLED(jquast): "New in version 3.3".
    # pylint: E1101 / Module 'zipfile' has no 'ZIP_BZIP2' member
    # 'bz2': functools.partial(diz_from_zip, method=zipfile.ZIP_BZIP2),
    # 'bzip2': functools.partial(diz_from_zip, method=zipfile.ZIP_BZIP2),
}


def main():
    """
    file browser

    add support for other archive types by adding their extension and mapped
    FILE_ID.DIZ extractor function to the `diz_extractors` dict in the
    config section of this file
    """
    session, term = getsession(), getterminal()
    session.activity = u'Browsing files'

    root = get_ini(section='sftp', key='root') or '/usr/share/misc'
    uploads_dir = os.path.join(root, '__uploads__')
    db_desc = DBProxy(DIZ_DB)

    # set syncterm font, if any
    if syncterm_font and term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    # for storing variables across ~10 functions, this is why all of the
    # functions have to be local to main(), because too much global state
    # is shared across them -- a class should have been used in such cases.
    browser = {
        'diz_location': 0,
        'last_diz_len': 0,
        'max_diz_width': 0,
        'max_diz_height': 0,
        'flagged_files': set(),
    }

    lightbar = Lightbar(height=term.height,
                        width=min(10, int(term.width * 0.25)),
                        xpos=0, ypos=0,
                        colors={'border': getattr(term, color_border),
                                'highlight': getattr(term, color_highlight)})

    # load flagged files
    browser['flagged_files'] = session.user.get('flaggedfiles', set())

    # remove missing files/dirs from flagged files, just in case
    if len(browser['flagged_files']):
        for filepath in browser['flagged_files'][:]:
            if not os.path.exists(filepath):
                browser['flagged_files'].remove(filepath)
        session.user['flaggedfiles'] = browser['flagged_files']

    def download_files(protocol='xmodem1k'):
        """ download flagged files """
        if not len(browser['flagged_files']):
            return False
        echo(term.clear)
        flagged = browser['flagged_files'].copy()
        for fname in flagged:
            _fname = fname[fname.rfind(os.path.sep) + 1:].decode('utf8')
            echo(term.bold_green(
                u'Start your {protocol} receiving program '
                u'to begin transferring {_fname}...\r\n'
                .format(protocol=protocol, _fname=_fname)))
            echo(u'Press ^X twice to cancel\r\n')

            fin = open(fname, 'rb')
            if not send_modem(fin, protocol):
                echo(term.bold_red(u'Transfer failed!\r\n'))
            else:
                browser['flagged_files'].remove(fname)
                session.user['flaggedfiles'] = browser['flagged_files']
                echo(term.bold(u'Transfer(s) finished.\r\n'))
        term.inkey()

    def upload_files(protocol='xmodem1k'):
        """ upload files """
        echo(term.clear)
        while True:
            echo(u'Filename (empty to quit):\r\n')
            led = LineEditor(width=term.width - 1)
            led.refresh()
            inp = led.read()
            led = None
            if inp:
                for illegal in (os.path.sep, u'..', u'~',):
                    if illegal in inp:
                        echo(term.bold_red(u'\r\nIllegal filename.\r\n'))
                        term.inkey()
                        return
                echo(term.bold(u'\r\nBegin your {0} sending program now.\r\n'
                               .format(protocol)))
                upload = open(os.path.join(
                    uploads_dir, inp), 'wb')
                if not recv_modem(upload, protocol):
                    echo(term.bold_red(u'Upload failed!\r\n'))
                else:
                    echo(term.bold_green(u'Transfer succeeded.\r\n'))
                term.inkey()
            else:
                return

    def draw_interface():
        """ redraw and resize the interface """

        lightbar.height = term.height
        lightbar.width = max(10, int(term.width * 0.25))

        # +1 for spacing between lightbar and diz
        browser['diz_location'] = lightbar.width + 1

        # -4 for lightbar borders and space before/after diz area
        browser['max_diz_width'] = term.width - lightbar.width - 4

        # -4 for space above/below diz area and info line (filename, size)
        browser['max_diz_height'] = term.height - 4

        echo(u''.join(term.clear,
                      lightbar.border(),
                      lightbar.refresh()))

    def clear_diz():
        """ clear file_id.diz area """

        echo(term.move(1, browser['diz_location']))
        # +2 for info line (filename, size) and empty line below it
        for i in range(browser['last_diz_len'] + 2):
            echo(u''.join((
                term.move(i, browser['diz_location']), term.clear_eol)))

    def describe_file(diz, directory, filename, isdir=None):
        """ describe a file in the diz area """
        if isdir or filename == u'..{0}'.format(os.path.sep):
            # describe directory
            description = u'{txt_Directory}: {filename}'.format(
                txt_Directory=term.bold(u'Directory'),
                filename=filename.decode('utf8'))

        else:
            # describe file
            _size = filesize(os.path.join(directory, filename))
            _filename = (filename[len(root):].decode('utf8')
                         if directory == os.path.join(root, flagged_dirname)
                         else filename.decode('utf8'))
            description = (u'{txt_Filename}: {filename}  {txt_Size}: {size}'
                           .format(txt_Filename=term.bold(u'Filename'),
                                   filename=_filename,
                                   txt_Size=term.bold(u'Size'),
                                   size=_size))
        echo(u''.join((term.move(1, browser['diz_location']),
                       description,
                       term.move(3, browser['diz_location']))))

        wrapped_diz = []
        for line in diz[:browser['max_diz_height']]:
            wrapped_diz += term.wrap(line, browser['max_diz_width'])

        output = u''
        for line in wrapped_diz:
            browser['last_diz_len'] += 1
            output = u''.join(
                (output, term.move_x(browser['diz_location']),
                 line, u'\r\n'))
        echo(output)

    def mark_flagged(directory, files):
        """ add marker to flagged files """

        files_list = list()
        for fname in files:
            prefix = u' '
            if os.path.join(directory, fname) in browser['flagged_files']:
                prefix = flagged_char
            txt_fname = fname.strip().decode('utf8')
            item = (fname, (u'{prefix}{txt_fname}'
                            .format(prefix=prefix, txt_fname=txt_fname)))
            files_list.append(item)
        return files_list

    def flagged_listdir():
        """ build listing for flagged files pseudo-folder """

        files = [u'{flagged_char}{txt_fname}'.format(
            flagged_char=flagged_char,
            txt_fname=fname[fname.rfind(os.path.sep) + 1:].decode('utf8'))
            for fname in browser['flagged_files']]

        zipped_files = zip(browser['flagged_files'], files)
        sorted_files = sorted(zipped_files, key=lambda x: x[1].lower())
        sorted_files.insert(0, (u'..{0}'.format(os.path.sep),
                                u' ..{0}'.format(os.path.sep)))
        return sorted_files

    def regular_listdir(directory, sub):
        """ build listing for regular folder """

        files = sorted(os.listdir(directory), key=lambda x: x.lower())
        sorted_dirs = []
        sorted_files = []
        for fname in files:
            filepath = os.path.join(directory, fname)
            # skip uploads folder
            if not session.user.is_sysop and filepath == uploads_dir:
                continue
            # designate dirs with path separator suffix
            if os.path.isdir(filepath):
                sorted_dirs.append('{0}{1}'.format(fname, os.path.sep))
            else:
                sorted_files.append(fname)

        if sub:
            # we are in a subdir; add '..' parent directory entry
            sorted_dirs.insert(0, '..%s' % os.path.sep)
        else:
            # we are in the root; add the flagged pseudo-folder
            sorted_dirs.insert(0, flagged_dirname)

        return mark_flagged(directory, sorted_dirs + sorted_files)

    def browse_dir(directory, sub=False):
        """ browse a directory """

        def reload_dir():
            """ reload contents of directory """

            if directory == os.path.join(root, flagged_dirname):
                # pseudo-folder for flagged files list
                lightbar.update(flagged_listdir())
            else:
                # actual folder
                lightbar.update(regular_listdir(directory, sub))

        def is_flagged_dir(directory):
            """ is this our __flagged__ directory? """

            return (directory == flagged_dirname or
                    directory.endswith(flagged_dirname))

        # build and sort directory listing
        reload_dir()
        echo(lightbar.refresh())
        filename, _ = lightbar.selection
        browser['last_diz_len'] = 0
        diz = ''
        # force it to describe the very first file when browser loads
        inp = lightbar.keyset['home'][0]

        # TODO(haliphax): prime the loop with defined values !!
        isdir = -1
        filepath = 'XXXXX'

        while True:
            # read from lightbar
            while not inp:
                inp = getch(0.20)
                # respond to screen dimension change by redrawing
                if session.poll_event('refresh'):
                    draw_interface()
                    describe_file(diz=diz, directory=directory,
                                  filename=filename, isdir=isdir)

            idx = lightbar.vitem_idx
            shift = lightbar.vitem_shift

            # pass input to lightbar
            lightbar.process_keystroke(inp)

            if inp in lightbar.keyset['home']:
                # lightbar 'home' keystroke bug; redraw current line
                echo(lightbar.refresh_row(idx))
                echo(lightbar.refresh_row(lightbar.vitem_idx))

            elif lightbar.quit:
                # 'exit' key pressed
                return False

            elif inp in (u' ',) and filename[-1:] != os.path.sep:
                # 'flag' key pressed; don't allow flagging directories
                if filepath in browser['flagged_files']:
                    # already flagged; un-flag
                    browser['flagged_files'].remove(filepath)
                else:
                    browser['flagged_files'].add(filepath)

                session.user['flaggedfiles'] = browser['flagged_files']
                reload_dir()

                if is_flagged_dir(directory):
                    echo(lightbar.refresh())
                else:
                    echo(lightbar.refresh_row(lightbar.vitem_idx))
                    lightbar.move_down()

            elif inp in (u'-',):
                # 'unflag all' pressed
                session.user['flaggedfiles'] = browser['flagged_files'] = set()
                reload_dir()
                echo(lightbar.refresh())
            elif inp in (u'd',) and len(browser['flagged_files']):
                download_files()
                reload_dir()
                draw_interface()
            elif inp in (u'u',):
                upload_files()
                reload_dir()
                draw_interface()

            clear_diz()
            filename, _ = lightbar.selection

            # figure out file extension
            filepath = os.path.join(directory, filename)
            relativename = filepath[len(root):]
            isdir = bool(filepath[-1:] == os.path.sep)
            ext = None
            rfind = filename.rfind('.')
            if rfind > -1:
                ext = filename[rfind + 1:].lower()

            save_diz = True
            if lightbar.selected or inp in (term.KEY_LEFT, term.KEY_RIGHT,):
                # 'select' key pressed

                if sub and inp is term.KEY_LEFT:
                    # term.KEY_LEFT backs up
                    return True

                if (isdir or is_flagged_dir(filename) and (
                        lightbar.selected or inp is term.KEY_RIGHT)):

                    if filename == '..{0}'.format(os.path.sep):
                        # is directory and is a parent directory; back out
                        return True

                    # RECURSION
                    if not browse_dir(filepath, True):
                        # sub directory; jump in
                        return False

                    reload_dir()
                    lightbar.vitem_shift = shift
                    lightbar.vitem_idx = idx
                    echo(lightbar.refresh())

            if relativename in db_desc:
                save_diz = False
                diz = decode_colly(session=session,
                                   diz_data=db_desc[relativename],
                                   extension=ext)

            elif ext in DIZ_EXTRACTORS:
                # is (supported) archive
                diz = DIZ_EXTRACTORS[ext](filepath).split('\n')

            elif ext in colly_extensions:
                # is ASCII colly, pull diz from between markers if available.
                diz = get_diz_from_colly(
                    session=session, filepath=filepath
                ) or diz

            elif is_flagged_dir(filename):
                # is pseudo-folder for flagged files
                save_diz = False
                diz = get_instructions(term)

            elif isdir:
                # is directory; don't give it a description
                save_diz = False
                diz = []

            else:
                # is normal file
                save_diz = False
                diz = [u'No description']

            if not uploads_dir.find(directory) and save_diz:
                # write description to diz db when save_diz is True
                with db_desc:
                    db_desc[relativename] = diz

            browser['last_diz_len'] = len(diz)
            describe_file(diz=diz, directory=directory,
                          filename=filename, isdir=isdir)
            echo(lightbar.refresh_quick() + lightbar.fixate())
            inp = None

    # fire it up!
    draw_interface()
    browse_dir(root)
    echo(term.move(term.height - 1, 0))
    echo(u'\r\n\r\n' + term.normal)
