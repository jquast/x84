"""
 Main menu script for x/84, http://github.com/jquast/x84
"""

#pylint: disable=W0614
#        Unused import from wildcard import
from bbs import *

def refresh():
    " refresh main menu screen "
    term = getterminal ()
    echo (u''.join((term.normal, term.normal_cursor, term.clear, '\r\n')))
    art = ([Ansi(from_cp437(line)) for line in open('default/art/main.asc')])
    max_len = max([line.__len__() for line in art])
    if max_len <= term.width:
        for line in art:
            echo (line.center(term.width).rstrip() + '\r\n')
    def disp_entry(char, blurb):
        return Ansi(term.bold_blue('(') + term.blue_reverse(char)
                + term.bold_blue + ')' + term.bright_white (' '+blurb))
    echo (term.move(len(art) - 10, term.width / 4) or '\r\n')
    echo (disp_entry ('b', 'bbs lister').ljust(term.width/5))
    echo (disp_entry ('l', 'last calls').ljust(term.width/5))
    echo (disp_entry ('o', 'one liners').ljust(term.width/5))
    echo (term.move(len(art) - 8, term.width / 4) or '\r\n')
    echo (disp_entry ('z', 'news').ljust(term.width/5))
    echo (disp_entry ('g', 'goodbye').ljust(term.width/5))
    echo (disp_entry ('c', 'charset').ljust(term.width/5))
    echo (disp_entry ('r', 'vi .nethackrc').ljust(term.width/5))
    echo (disp_entry ('p', 'vi .plan').ljust(term.width/5))
    echo (u'\r\n\r\n')

def edit_nhrc():
    session, term = getsession(), getterminal()
    editor = '/usr/local/bin/virus'
    if session.user.handle == u'anonymous':
        echo (u''.join((u'\r\n', term.bold_red, msg_anon_noedit, temr.normal)))
        getch (2)
        prompt ()
        continue # denied
    fp, tmppath = tempfile.mkstemp ()
    nethackrc = session.user.get('.nethackrc', '')
    length = len(nethackrc)
    if 0 != length:
        written = 0
        while written < length:
            written += os.write (fp, nethackrc[written:])
    os.close (fp)
    lastmod = os.stat(tmppath).st_mtime
    d = Door(editor, args=(tmppath,))
    d._TAP = True
    if 0 == d.run() and os.stat(tmppath).st_mtime > lastmod:
        # program exited normaly, file has been modified
        fp = open(tmppath, 'r')
        session.user.set('.nethackrc', fp.read())
        fp.close ()
        session.user.save ()
    os.unlink (tmppath)

def main():
    session, term = getsession(), getterminal()

    dirty = True
    while True:
        if pollevent('refresh'):
            dirty = True
        if dirty:
            dirty = False
            refresh()
        choice = getch(1)
        if choice == u'*':
            goto ('main')
        elif choice == u'b':
            gosub ('bbslist')
            dirty = True
        elif choice == u'l':
            gosub ('lc')
            dirty = True
        elif choice == u'o':
            gosub ('ol')
            dirty = True
        elif choice == u'z':
            gosub('news')
            dirty = True
        elif choice == u'g':
            goto('logoff')
        elif choice == u'c':
            gosub('charset')
            dirty = True
        elif choice == u'r':
            gosub('editor', '.nethackrc')
        elif choice == u'p':
            gosub('editor', '.plan')
