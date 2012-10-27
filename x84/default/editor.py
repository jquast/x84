import tempfile
import os
#pylint: disable=W0614
#        Unused import from wildcard import
from x84.bbs import *

def main(sattr):
    session, term = getsession(), getterminal()
    editor = '/usr/local/bin/virus'
    fp, tmppath = tempfile.mkstemp ()
    nethackrc = session.user.get(sattr, '')
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
        session.user[sattr] = open(tmppath, 'r').fp.read()
    os.unlink (tmppath)
