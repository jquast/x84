import logging
import time
import os

def main():
    from x84.bbs import getsession, getterminal, gosub, echo, ini
    from x84.bbs import showcp437, getch, Door, LineEditor, Ansi
    from x84.bbs import list_users

    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    assert ini.CFG.getboolean('dosemu', 'enabled'), (
        'lord.py called but dosemu not enabled in ini.CFG')
    dosemu_bin = ini.CFG.get('dosemu', 'bin')
    lord_doorsys = ini.CFG.get('dosemu', 'lord_doorsys')
    lord_drive = ini.CFG.get('dosemu', 'lord_drive')
    lord_path = ini.CFG.get('dosemu', 'lord_path')
    door_bat = ini.CFG.get('dosemu', 'door_bat')
    door_lck = ini.CFG.get('dosemu', 'door_lck')
    d = Door(dosemu_bin, args=('-u', 'virtual', '-I', "keystroke '\r'",))
    d.decode_cp437 = True # lord is in cp437 encoding
    node = -1
    for n in range(1, 32):
        event = 'lock-%s/%d' % ('node', n)
        echo('%s\r\n' % (event,))
        session.send_event(event, ('acquire', None))
        data = session.read_event(event)
        echo('%s\r\n' % (data,))
        if data is True:
            node=n
            break
    event = 'lock-%s/%d' % ('node', node)
    stale=0
    while os.path.exists(door_lck) and stale < 3:
        echo(u'Waiting for lock ..\r\n')
        stale += 1
        time.sleep(1)
    if not os.path.exists(door_lck):
       open(door_lck, 'w').close()
    with open(door_bat, 'w') as fp:
        fp.write('%s\r\n' % (lord_drive,))
        fp.write('cd %s\r\n' % (lord_path,))
        fp.write('call start.bat %d\r\n' % (node,))
        fp.write('exitemu\r\n')
    with open(lord_doorsys, 'w') as fp:
        fp.write('COM1:\r\n')
        fp.write('587600\r\n')
        fp.write('8\r\n')
        fp.write('%d\r\n' % (node,))
        fp.write('587600\r\n')
#        fp.write('N\r\n')
        fp.write('Y\r\n' * 4)
        fp.write('%s\r\n' % (session.user.handle.upper(),))
        fp.write('No City Supplied\r\n' * 3)
        fp.write('<encrypted>1\r\n')
        fp.write('2551\r\n' if session.user.is_sysop else '1001\r\n')
        fp.write('1\r\n')
        fp.write('%s\r\n' % (time.strftime('%m/%d/%y'),))
        fp.write('%d\r\n' % (256 * 60,))
        fp.write('%d\r\n' % (256,))
        fp.write('NG\r\n')
        fp.write('%d\r\n' % (term.height))
        fp.write('%s\r\n' % (
            'Y' if session.user.get('expert', False) else 'N',))
        fp.write('1,2,3,4,5,6,7\r\n')
        fp.write('1\r\n')
        fp.write('01/01/99\r\n')
        fp.write('%d\r\n' % list_users().index(session.user.handle))
        fp.write('X\r\n')
        fp.write('0\r\n' * 3)
        fp.write('9999\r\n')
        fp.write('09/09/99\r\n')
        fp.write('C:\\r\n')
        fp.write('C:\\r\n')
        fp.write('n/a\r\n')
        fp.write('%s\r\n' % (session.user.handle,))
        fp.write('00:00\r\n')
        fp.write('Y\r\n')
        fp.write('N\r\n')
        fp.write('Y\r\n')
        fp.write('14\r\n')
        fp.write('999\r\n')
        fp.write('09/09/99\r\n')
        fp.write('00:00\r\n')
        fp.write('00:00\r\n')
        fp.write('999\r\n')
        fp.write('999\r\n')
        fp.write('0\r\n')
        fp.write('0\r\n')
        fp.write('none\r\n')
        fp.write('0\r\n')
        fp.write('0\r\n')
        fp.close()
    nlines = len(open(lord_doorsys).readlines())
    assert(nlines == 52)
    echo(u'Node %d ...\r\n' % (node,))
    d.run()  # begin door
    if os.path.exists(door_lck):
       os.unlink(door_lck)
    session.send_event(event, ('release', None))
