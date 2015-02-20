""" File browser/manager for x/84. """
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

#: root folder for the filebase
ROOT = get_ini(section='sftp', key='root') or '/usr/share/misc'

#: directory for storing uploads
UPLOADS_DIR = os.path.join(ROOT, '__uploads__')

#: color used for menu key entries
COLOR_HIGHLIGHT = get_ini(
    section='fbrowse', key='color_highlight'
) or 'bold_white_on_blue'

#: color used for borders
COLOR_BORDER = get_ini(
    section='fbrowse', key='color_border',
) or 'bold_blue'

#: fontset for SyncTerm emulator
SYNCTERM_FONT = get_ini(
    section='fbrowse', key='syncterm_font'
) or 'cp437'

#: marker for flagged files in browser list
FLAGGED_CHAR = get_ini(
    section='fbrowse', key='flagged_char'
) or u'+'

#: extensions for ASCII collies
COLLY_EXTENSIONS = get_ini(
    section='fbrowse', key='colly_extensions', split=True
) or ['.txt', '.asc', '.ans']

#: name of virtual directory for collecting user's flagged files
FLAGGED_DIRNAME = get_ini(
    section='fbrowse', key='flagged_dirname'
) or u'__flagged__{0}'.format(os.path.sep)

#: decoding to use for ASCII collies
COLLY_DECODING = get_ini(
    section='fbrowse', key='colly_decoding'
) or 'amiga'


class FileBrowser(object):

    """ File browsing interface variables that need to be passed around """

    # pylint:disable=R0903
    diz_location = 0
    last_diz_len = 0
    max_diz_width = 0
    max_diz_height = 0
    flagged_files = set()
    diz_extractors = dict()

# instance to be used throughout the script
browser = FileBrowser()  # pylint:disable=C0103


def diz_from_dms(binary, filename):
    """
    Amiga diskmasher format. Depends on the external binary 'xdms'.
    """
    import subprocess
    args = ('d', filename)
    proc = subprocess.Popen((binary,) + args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    output, _ = proc.communicate()
    if proc.returncode == 0:
        return output.decode('cp437_art')
    else:
        return u'No description'


def diz_from_lha(binary, filename):
    """
    Amiga LHA format. Depends on the external binary 'lha'.
    """
    import subprocess
    import tempfile
    import shutil
    description = u'No description'
    path = tempfile.mkdtemp(prefix='x84_')
    args = ('xw={0}'.format(path), filename)
    proc = subprocess.Popen((binary,) + args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    proc.wait()
    dizfilename = os.path.join(path, 'file_id.diz')
    if proc.returncode == 0 and os.path.isfile(dizfilename):
        with open(dizfilename, 'rb') as dizfile:
            description = dizfile.read().decode('cp437_art')
    try:
        shutil.rmtree(path)
    except OSError:
        pass
    return description


def diz_from_zip(filename, method=zipfile.ZIP_STORED):
    """
    Pull FILE_ID.DIZ from `filename` using particular zipfile `method`.
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


def get_diz_from_colly(filepath):
    """ Get FILE_ID.DIZ from within an ASCII collection. """
    colly = open(filepath, 'r').read()
    colly_diz_begin = '@BEGIN_FILE_ID.DIZ'
    colly_diz_end = '@END_FILE_ID.DIZ'
    pos = colly.find(colly_diz_begin)
    if pos > 0:
        colly = colly[pos + len(colly_diz_begin):]
        pos = colly.find(colly_diz_end)
        if pos > 0:
            return colly[:pos].splitlines()
    return None


def get_instructions(term, is_sysop=None):
    """ Show file browser instructions. """
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
        .format(term.reverse(u'(u)')),
        u'{0}     Edit description'
        .format(term.reverse(u'(e)')) if is_sysop else u'',
        u'{0}     Quit'
        .format(term.reverse(u'(q)')),
        u' ',
        u'Files are also available via {0}'
        .format(term.bold(u'SFTP')),
    ]


def edit_description(filepath, db_desc):
    """ Edit file description. """
    from x84.bbs import gosub
    new_desc = None
    if filepath in db_desc:
        new_desc = u'\r\n'.join([line.decode('cp437_art')
                                 for line in db_desc[filepath]])
    new_desc = gosub('editor', continue_draft=new_desc)
    if not new_desc:
        return
    with db_desc:
        db_desc[filepath] = new_desc.splitlines()


def download_files(term, session, protocol='xmodem1k'):
    """ Download flagged files. """
    if not len(browser.flagged_files):
        return False
    echo(term.clear)
    flagged = browser.flagged_files.copy()
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
            browser.flagged_files.remove(fname)
            session.user['flaggedfiles'] = browser.flagged_files
            echo(term.bold(u'Transfer(s) finished.\r\n'))
    term.inkey()


def upload_files(term, protocol='xmodem1k'):
    """ Upload files. """
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

            echo(term.bold(
                u'\r\nBegin your {0} sending program now.\r\n'
                .format(protocol)))

            upload_filename = os.path.join(UPLOADS_DIR, inp)
            try:
                upload = open(upload_filename, 'wb')
            except IOError as err:
                echo(term.bold_red('u\r\nIOError: {err}\r\n'.format(err=err)))
            else:
                if not recv_modem(upload, protocol):
                    echo(term.bold_red(u'Upload failed!\r\n'))
                    os.unlink(upload_filename)
                else:
                    echo(term.bold_green(u'Transfer succeeded.\r\n'))
            term.inkey()
        else:
            return


def draw_interface(term, lightbar):
    """ Redraw and resize the interface. """
    lightbar.height = term.height
    lightbar.width = max(10, int(term.width * 0.25))
    # +1 for spacing between lightbar and diz
    browser.diz_location = lightbar.width + 1
    # -2 for spacing between the lightbar, the diz, and the edge of the screen
    browser.max_diz_width = term.width - lightbar.width - 2
    # -4 for space above/below diz area and info line (filename, size)
    browser.max_diz_height = term.height - 4
    echo(u''.join([term.clear,
                   lightbar.border(),
                   lightbar.refresh()]))


def clear_diz(term):
    """ Clear file_id.diz area. """
    echo(term.move(1, browser.diz_location))
    # +2 for info line (filename, size) and empty line below it
    for i in range(browser.last_diz_len + 2):
        echo(u''.join((
            term.move(i, browser.diz_location), term.clear_eol)))


def describe_file(term, diz, directory, filename, isdir=None):
    """ Describe a file in the diz area. """
    if isdir or filename == u'..{0}'.format(os.path.sep):
        # describe directory
        description = u'{txt_Directory}: {filename}'.format(
            txt_Directory=term.bold(u'Directory'),
            filename=filename.decode('utf8'))

    else:
        # describe file
        _size = filesize(os.path.join(directory, filename))
        _filename = (filename[len(ROOT):].decode('utf8')
                     if directory == os.path.join(ROOT, FLAGGED_DIRNAME)
                     else filename.decode('utf8'))
        description = (u'{txt_Filename}: {filename}  {txt_Size}: {size}'
                       .format(txt_Filename=term.bold(u'Filename'),
                               filename=_filename,
                               txt_Size=term.bold(u'Size'),
                               size=_size))

    description = term.wrap(description, browser.max_diz_width)
    echo(u''.join((term.move(1, browser.diz_location),
                   u''.join(['{0}{1}\r\n'.format(
                             term.move_x(browser.diz_location), line)
                             for line in description]),
                   term.move(2 + len(description), browser.diz_location))))

    wrapped_diz = []
    for line in diz:
        wrapped_diz += term.wrap(line, browser.max_diz_width)
    wrapped_diz = wrapped_diz[:browser.max_diz_height - len(description) + 1]

    output = u''
    for line in wrapped_diz:
        browser.last_diz_len += 1
        output = u''.join(
            (output, term.move_x(browser.diz_location),
             line, u'\r\n'))
    echo(output)


def mark_flagged(directory, files):
    """ Add marker to flagged files. """
    files_list = list()
    for fname in files:
        prefix = u' '
        if os.path.join(directory, fname) in browser.flagged_files:
            prefix = FLAGGED_CHAR
        txt_fname = fname.strip().decode('utf8')
        item = (fname, (u'{prefix}{txt_fname}'
                        .format(prefix=prefix, txt_fname=txt_fname)))
        files_list.append(item)
    return files_list


def flagged_listdir():
    """ Build listing for flagged files pseudo-folder. """
    files = [u'{flagged_char}{txt_fname}'.format(
        flagged_char=FLAGGED_CHAR,
        txt_fname=fname[fname.rfind(os.path.sep) + 1:].decode('utf8'))
        for fname in browser.flagged_files]

    zipped_files = zip(browser.flagged_files, files)
    sorted_files = sorted(zipped_files, key=lambda x: x[1].lower())
    sorted_files.insert(0, (u'..{0}'.format(os.path.sep),
                            u' ..{0}'.format(os.path.sep)))
    return sorted_files


def regular_listdir(session, directory, sub):
    """ Build listing for regular folder. """
    files = sorted(os.listdir(directory), key=lambda x: x.lower())
    sorted_dirs = []
    sorted_files = []
    for fname in files:
        filepath = os.path.join(directory, fname)
        # skip uploads folder
        if not session.user.is_sysop and filepath == UPLOADS_DIR:
            continue
        # designate dirs with path separator suffix
        if os.path.isdir(filepath):
            sorted_dirs.append('{0}{1}'.format(fname, os.path.sep))
        else:
            sorted_files.append(fname)

    if sub:
        # we are in a subdir; add '..' parent directory entry
        sorted_dirs.insert(0, '..{0}'.format(os.path.sep))
    else:
        # we are in the root; add the flagged pseudo-folder
        sorted_dirs.insert(0, FLAGGED_DIRNAME)

    return mark_flagged(directory, sorted_dirs + sorted_files)


def reload_dir(session, directory, lightbar, sub):
    """ Reload contents of directory. """
    if directory == os.path.join(ROOT, FLAGGED_DIRNAME):
        # pseudo-folder for flagged files list
        lightbar.update(flagged_listdir())
    else:
        # actual folder
        lightbar.update(regular_listdir(session, directory, sub))


def is_flagged_dir(directory):
    """ Check to see if this is the __flagged__ directory. """
    return (directory == FLAGGED_DIRNAME or
            directory.endswith(FLAGGED_DIRNAME))


def browse_dir(session, db_desc, term, lightbar, directory, sub=False):
    """ Browse a directory. """
    # build and sort directory listing
    reload_dir(session, directory, lightbar, sub)
    echo(lightbar.refresh())
    filename, _ = lightbar.selection
    browser.last_diz_len = 0
    diz = ''
    # force it to describe the very first file when browser loads
    inp = lightbar.keyset['home'][0]
    # prime our loop
    isdir = False
    filepath = ''

    while True:
        # read from lightbar
        while not inp:
            inp = getch(0.2)
            # respond to screen dimension change by redrawing
            if session.poll_event('refresh'):
                draw_interface(term, lightbar)
                describe_file(term, diz=diz, directory=directory,
                              filename=filename, isdir=isdir)

        idx = lightbar.vitem_idx
        shift = lightbar.vitem_shift

        # pass input to lightbar
        lightbar.process_keystroke(inp)
        filename, _ = lightbar.selection

        filepath = os.path.join(directory, filename)
        relativename = filepath[len(ROOT):]
        isdir = bool(filepath[-1:] == os.path.sep)
        _, ext = os.path.splitext(filename.lower())

        if inp in lightbar.keyset['home']:
            # lightbar 'home' keystroke bug; redraw current line
            echo(lightbar.refresh_row(idx))
            echo(lightbar.refresh_row(lightbar.vitem_idx))

        elif lightbar.quit:
            # 'exit' key pressed
            return False

        elif inp in (u' ',) and filename[-1:] != os.path.sep:
            # 'flag' key pressed; don't allow flagging directories
            if filepath in browser.flagged_files:
                # already flagged; un-flag
                browser.flagged_files.remove(filepath)
            else:
                browser.flagged_files.add(filepath)

            session.user['flaggedfiles'] = browser.flagged_files
            reload_dir(session, directory, lightbar, sub)

            if is_flagged_dir(directory):
                echo(lightbar.refresh())
            else:
                echo(lightbar.refresh_row(lightbar.vitem_idx))
                lightbar.move_down()

        elif inp in (u'-',):
            # 'unflag all' pressed
            session.user['flaggedfiles'] = browser.flagged_files = set()
            reload_dir(session, directory, lightbar, sub)
            echo(lightbar.refresh())

        elif inp in (u'd',) and len(browser.flagged_files):
            download_files(term, session)
            reload_dir(session, directory, lightbar, sub)
            draw_interface(term, lightbar)

        elif inp in (u'u',):
            upload_files(term)
            reload_dir(session, directory, lightbar, sub)
            draw_interface(term, lightbar)

        elif inp in (u'e',) and session.user.is_sysop and not isdir:
            edit_description(relativename, db_desc)
            reload_dir(session, directory, lightbar, sub)
            draw_interface(term, lightbar)

        clear_diz(term)
        save_diz = True

        if lightbar.selected or inp in (term.KEY_LEFT, term.KEY_RIGHT,):

            if sub and inp is term.KEY_LEFT:
                # term.KEY_LEFT backs up
                return True

            if (isdir or is_flagged_dir(filename) and (
                    lightbar.selected or inp is term.KEY_RIGHT)):
                # 'select' key pressed

                if filename == '..{0}'.format(os.path.sep):
                    # is directory and is a parent directory; back out
                    return True

                # RECURSION
                if not browse_dir(session, db_desc, term, lightbar,
                                  filepath, True):
                    # sub directory; jump in
                    return False

                reload_dir(session, directory, lightbar, sub)
                lightbar.vitem_shift = shift
                lightbar.vitem_idx = idx
                echo(lightbar.refresh())

        if relativename in db_desc:
            save_diz = False
            diz = db_desc[relativename]
            if ext in COLLY_EXTENSIONS:
                decoder = 'cp437_art'
                if session.encoding == 'utf8':
                    decoder = COLLY_DECODING
                try:
                    diz = [line.decode(decoder, errors='replace')
                           for line in diz]
                except UnicodeEncodeError:
                    diz = [u'Invalid characters in FILE_ID.DIZ']

        elif ext in browser.diz_extractors:
            # is (supported) archive
            diz = browser.diz_extractors[ext](filepath).splitlines()

        elif ext in COLLY_EXTENSIONS:
            # is ASCII colly, pull diz from between markers if available.
            diz = get_diz_from_colly(filepath=filepath) or diz
            # save diz in raw format, but display decoded
            save_diz = False
            db_desc[relativename] = diz
            decoder = 'cp437_art'
            if session.encoding == 'utf8':
                decoder = COLLY_DECODING
            try:
                diz = [line.decode(decoder, errors='replace') for line in diz]
            except UnicodeEncodeError:
                diz = [u'Invalid characters in FILE_ID.DIZ']
                db_desc[relativename] = diz

        elif is_flagged_dir(filename):
            # is pseudo-folder for flagged files
            save_diz = False
            diz = get_instructions(term, session.user.is_sysop)

        elif isdir:
            # is directory; don't give it a description
            save_diz = False
            diz = []

        else:
            # is normal file
            save_diz = False
            diz = [u'No description']

        if not UPLOADS_DIR.find(directory) and save_diz:
            # write description to diz db when save_diz is True
            with db_desc:
                db_desc[relativename] = diz

        browser.last_diz_len = len(diz)
        describe_file(term=term, diz=diz, directory=directory,
                      filename=filename, isdir=isdir)
        echo(lightbar.refresh_quick() + lightbar.fixate())
        inp = None


def main():
    """ File browser launch point. """
    import subprocess
    import functools
    session, term = getsession(), getterminal()
    session.activity = u'Browsing files'
    db_desc = DBProxy(DIZ_DB)

    # set syncterm font, if any
    if SYNCTERM_FONT and term.kind.startswith('ansi'):
        echo(syncterm_setfont(SYNCTERM_FONT))

    # assign extractors to file types
    browser.diz_extractors['.zip'] = diz_from_zip

    # detect LHA and DMS support
    output, _ = subprocess.Popen(('which', 'lha'), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).communicate()
    if output:
        browser.diz_extractors['.lha'] = functools.partial(diz_from_lha,
                                                          output.rstrip())
    output, _ = subprocess.Popen(('which', 'xdms'), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).communicate()
    if output:
        browser.diz_extractors['.dms'] = functools.partial(diz_from_dms,
                                                          output.rstrip())

    # load flagged files
    browser.flagged_files = session.user.get('flaggedfiles', set())

    # remove missing files/dirs from flagged files, just in case
    if len(browser.flagged_files):
        for filepath in list(browser.flagged_files)[:]:
            if not os.path.exists(filepath):
                browser.flagged_files.remove(filepath)
        session.user['flaggedfiles'] = browser.flagged_files

    # fire it up!
    lightbar = Lightbar(height=term.height,
                        width=min(10, int(term.width * 0.25)),
                        xloc=0, yloc=0,
                        colors={'border': getattr(term, COLOR_BORDER),
                                'highlight': getattr(term, COLOR_HIGHLIGHT)})
    draw_interface(term, lightbar)
    with term.hidden_cursor():
        browse_dir(session, db_desc, term, lightbar, ROOT)
    echo(term.move(term.height, term.width))
    echo(u'\r\n\r\n' + term.normal)
