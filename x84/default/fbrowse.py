""" File browsing/tagging for x/84 bbs https://github.com/jquast/x84 """

from __future__ import division
import zipfile
import os


### archive extraction functions ###

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
        else:
            return u'No description'
    except zipfile.BadZipfile:
        return u'Bad zip file, cannot parse'
    except zipfile.LargeZipFile:
        # since we do allowZip64=True above, this shouldn't happen any longer
        return u'Large zip file, cannot parse'
    except NotImplementedError:
        return u'Unsupported compression, cannot parse'


def diz_from_bzip2(filename):
    """
    wrapper to call `diz_from_zip` using `zipfile.ZIP_BZIP2` method
    """

    return diz_from_zip(filename, method=zipfile.ZIP_BZIP2)


### config ###

# map extensions to helper functions for pulling FILE_ID.DIZ
diz_extractors = {
    'zip': diz_from_zip,
    'bz2': diz_from_bzip2,
    'bzip2': diz_from_bzip2,
}
# extensions for ASCII collies
colly_extensions = ['txt', 'asc', 'ans', ]
# decoding to use for ASCII collies
colly_decoding = 'amiga'
# character to denote flagged files
flagged_char = u'+'
# dirname for flagged listing
flagged_dirname = u'__flagged__%s' % os.path.sep


### script logic ###

# for storing 'global' vars to be used in sub-funcs/recursive calls
browser = {
    'diz_location': 0,
    'last_diz_len': 0,
    'max_diz_width': 0,
    'max_diz_height': 0,
    'flagged_files': set(),
}

# file description database
DIZ_DB = 'filediz'


def main():
    """
    file browser

    add support for other archive types by adding their extension and mapped
    FILE_ID.DIZ extractor function to the `diz_extractors` dict in the
    config section of this file
    """

    from x84.bbs import echo, getterminal, Lightbar, getch, getsession, DBProxy
    from x84.bbs.ini import CFG

    session, term = getsession(), getterminal()
    session.activity = u'Browsing files'

    root = CFG.get('sftp', 'root')
    uploads_dir = os.path.join(root, '__uploads__')
    # db for cached FILE_ID.DIZ descriptions
    descriptions = DBProxy(DIZ_DB)
    # setup lightbar
    lb_colors = {
        'border': term.blue,
        'highlight': term.bold_white_on_blue
    }
    lb = Lightbar(term.height, int(term.width * 0.25), 0, 0, colors=lb_colors)
    # load flagged files
    browser['flagged_files'] = session.user.get('flaggedfiles', set())
    # remove missing files/dirs from flagged files, just in case
    if len(browser['flagged_files']):
        flagged = browser['flagged_files'].copy()
        for f in browser['flagged_files']:
            if not os.path.exists(f):
                flagged.remove(f)
        session.user['flaggedfiles'] = browser['flagged_files'] = flagged

    def download_files(protocol='xmodem1k'):
        """ download flagged files """

        from x84.bbs import send_modem
        if not len(browser['flagged_files']):
            return False
        echo(term.clear)
        flagged = browser['flagged_files'].copy()
        for f in flagged:
            echo(term.bold_green(
                u'Start your {0} receiving program '
                u'to begin transferring {1}...\r\n'
                .format(protocol, f[f.rfind(os.path.sep) + 1:].decode('utf8')
                )))
            echo(u'Press ^X twice to cancel\r\n')
            dl = open(f, 'rb')
            if not send_modem(dl, protocol):
                echo(term.bold_red(u'Transfer failed!\r\n'))
            else:
                browser['flagged_files'].remove(f)
                session.user['flaggedfiles'] = browser['flagged_files']
        echo(term.bold(u'Transfer(s) finished.\r\n'))
        term.inkey()

    def upload_files(protocol='xmodem1k'):
        """ upload files """

        from x84.bbs import recv_modem, LineEditor
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

        lb.height = term.height
        lb.width = int(term.width * 0.25)
        # +1 for spacing between lightbar and diz
        browser['diz_location'] = lb.width + 1
        # -4 for lightbar borders and space before/after diz area
        browser['max_diz_width'] = term.width - lb.width - 4
        # -4 for space above/below diz area and info line (filename, size)
        browser['max_diz_height'] = term.height - 4
        echo(term.clear)
        echo(lb.border())
        echo(lb.refresh())

    def clear_diz():
        """ clear file_id.diz area """

        echo(term.move(1, browser['diz_location']))
        # +2 for info line (filename, size) and empty line below it
        for i in range(browser['last_diz_len'] + 2):
            echo(u''.join((
                term.move(i, browser['diz_location']), term.clear_eol)))

    def describe_file(diz, directory, filename, isdir=None):
        """ describe a file in the diz area """

        from common import filesize
        description = None
        # describe directory
        if isdir or filename == u'..%s' % os.path.sep:
            description = u'%s: %s' % (
                term.bold(u'Directory'),
                filename.decode('utf8')
            )
        # describe file
        else:
            fullname = os.path.join(directory, filename)
            size = filesize(fullname)
            description = u'%s: %s  %s: %s' % (
                term.bold(u'Filename'),
                filename[len(root):].decode('utf8')
                    if directory == os.path.join(root, flagged_dirname)
                    else filename.decode('utf8'),
                term.bold(u'Size'),
                size,
            )
        echo(term.move(1, browser['diz_location']))
        echo(description)
        echo(term.move(3, browser['diz_location']))
        wrapped_diz = []
        for line in diz[:browser['max_diz_height']]:
            wrapped_diz += term.wrap(line, browser['max_diz_width'])
        for line in wrapped_diz:
            browser['last_diz_len'] += 1
            echo(term.move_x(browser['diz_location']))
            echo(u'%s\r\n' % line)

    def mark_flagged(directory, files):
        """ add marker to flagged files """

        files_list = list()
        for f in files:
            if os.path.join(directory, f) not in browser['flagged_files']:
                files_list.append((f, u' %s' % f.strip().decode(
                    'utf8')))
            else:
                files_list.append((f, u'%s%s' % (flagged_char, f.strip().decode(
                    'utf8'))))
        return files_list

    def flagged_listdir():
        """ build listing for flagged files pseudo-folder """

        files = [u'%s%s' % (flagged_char, f[f.rfind(os.path.sep) + 1:].decode(
                 'utf8')) for f in browser['flagged_files']]
        zipped_files = zip(browser['flagged_files'], files)
        sorted_files = sorted(zipped_files, key=lambda x: x[1].lower())
        sorted_files.insert(0, (u'..%s' % os.path.sep, u' ..%s' % os.path.sep))
        return sorted_files

    def regular_listdir(directory, sub):
        """ build listing for regular folder """

        files = sorted(os.listdir(directory), key=lambda x: x.lower())
        sorted_dirs = []
        sorted_files = []
        for f in files:
            fullname = os.path.join(directory, f)
            # skip uploads folder
            if u'sysop' not in session.user.groups and \
                    fullname == uploads_dir:
                continue
            # designate dirs with path separator suffix
            if os.path.isdir(fullname):
                sorted_dirs.append('%s%s' % (f, os.path.sep))
            else:
                sorted_files.append(f)
        # we are in a subdir; add '..' parent directory entry
        if sub:
            sorted_dirs.insert(0, '..%s' % os.path.sep)
        # we are in the root; add the flagged pseudo-folder
        else:
            sorted_dirs.insert(0, flagged_dirname)
        files = mark_flagged(directory, sorted_dirs + sorted_files)
        return files

    def browse_dir(directory, sub=False):
        """ browse a directory """

        def reload_dir():
            """ reload contents of directory """

            lb_files = set()
            # pseudo-folder for flagged files list
            if directory == os.path.join(root, flagged_dirname):
                lb_files = flagged_listdir()
            # actual folder
            else:
                lb_files = regular_listdir(directory, sub)
            lb.update(lb_files)

        def is_flagged_dir(directory):
            """ is this our __flagged__ directory? """

            return directory == flagged_dirname or \
                directory.endswith(flagged_dirname)

        # build and sort directory listing
        reload_dir()
        echo(lb.refresh())
        filename, _ = lb.selection
        browser['last_diz_len'] = 0
        diz = ''
        # force it to describe the very first file when browser loads
        inp = lb.keyset['home'][0]

        while True:
            # read from lightbar
            while not inp:
                inp = getch(1)
                # respond to screen dimension change by redrawing
                if session.poll_event('refresh'):
                    draw_interface()
                    describe_file(diz, directory, filename, isdir)
            idx = lb.vitem_idx
            shift = lb.vitem_shift
            # pass input to lightbar
            lb.process_keystroke(inp)
            # lightbar 'home' keystroke bug; redraw current line
            if inp in lb.keyset['home']:
                echo(lb.refresh_row(idx))
                echo(lb.refresh_row(lb.vitem_idx))
            # 'exit' key pressed
            elif lb.quit:
                return False
            # 'tag' key pressed; don't allow tagging directories
            elif inp in (u' ',) and filename[-1:] != os.path.sep:
                # already flagged; untag
                if fullname in browser['flagged_files']:
                    browser['flagged_files'].remove(fullname)
                else:
                    browser['flagged_files'].add(fullname)
                session.user['flaggedfiles'] = browser['flagged_files']
                reload_dir()
                if is_flagged_dir(directory):
                    echo(lb.refresh())
                else:
                    echo(lb.refresh_row(lb.vitem_idx))
                    lb.move_down()
            # 'untag all' pressed
            elif inp in (u'-',):
                session.user['flaggedfiles'] = browser['flagged_files'] = set()
                reload_dir()
                echo(lb.refresh())
            elif inp in (u'd',) and len(browser['flagged_files']):
                download_files()
                reload_dir()
                draw_interface()
            elif inp in (u'u',):
                upload_files()
                reload_dir()
                draw_interface()
            clear_diz()
            filename, _ = lb.selection
            # figure out file extension
            fullname = os.path.join(directory, filename)
            relativename = fullname[len(root):]
            isdir = fullname[-1:] == os.path.sep
            ext = None
            rfind = filename.rfind('.')
            if rfind > -1:
                ext = filename[rfind + 1:].lower()
            save_diz = True
            # 'select' key pressed
            if lb.selected or inp in (term.KEY_LEFT, term.KEY_RIGHT,):
                # term.KEY_LEFT backs up
                if sub and inp is term.KEY_LEFT:
                    return True
                # is directory
                if (isdir or is_flagged_dir(filename)) \
                        and (lb.selected or inp is term.KEY_RIGHT):
                    # parent directory; back out
                    if filename == '..%s' % os.path.sep:
                        return True
                    # sub directory; jump in
                    if not browse_dir(fullname, True):
                        return False
                    reload_dir()
                    lb.vitem_shift = shift
                    lb.vitem_idx = idx
                    echo(lb.refresh())
            if relativename in descriptions:
                save_diz = False
                diz = descriptions[relativename]
                if ext in colly_extensions and session.encoding == 'utf8':
                    diz = [line.encode('cp437').decode(colly_decoding)
                           for line in diz]
            # is (supported) archive
            elif ext in diz_extractors:
                diz = diz_extractors[ext](fullname).split('\n')
            # is ASCII colly, pull diz from between markers
            elif ext in colly_extensions:
                colly = open(fullname, 'r').read()
                begin = '@BEGIN_FILE_ID.DIZ '
                end = '@END_FILE_ID.DIZ'
                pos = colly.find(begin)
                if pos:
                    colly = colly[pos + len(begin):]
                    pos = colly.find(end)
                    if pos:
                        if session.encoding == 'utf8':
                            diz = colly[:pos].decode(
                                colly_decoding).split('\n')
                        else:
                            diz = colly[:pos].decode('cp437_art').split('\n')
            # is pseudo-folder for flagged files
            elif is_flagged_dir(filename):
                save_diz = False
                diz = [
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
            # is directory; don't give it a description
            elif isdir:
                save_diz = False
                diz = []
            # is normal file
            else:
                save_diz = False
                diz = [u'No description']
            # write description to diz db?
            if not uploads_dir.find(directory) and save_diz:
                with descriptions:
                    descriptions[relativename] = diz
            browser['last_diz_len'] = len(diz)
            describe_file(diz, directory, filename, isdir)
            echo(lb.refresh_quick())
            echo(lb.fixate())
            inp = None

    # fire it up!
    draw_interface()
    browse_dir(root)
    echo(term.height - 1 + u'\r\n\r\n' + term.normal)
