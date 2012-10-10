
def main():
    session = getsession()
    session.activity = 'Checking for new messages'
    term = session.terminal

    echo (term.move(0,0) + term.clear + term.normal)
    showfile ('art/msgs.asc')

    # check for new private messages
    echo ('\r\n\r\n  Checking for private messages... ')

    # privmsgs returns message record numbers only
    privmsgs = msgbase.listprivatemsgs(recipient=session.handle)
    newmsgs = [msg for msg in privmsgs if not getmsg(msg).read]

    echo ('%s messages, %s new\r\n' % (len(privmsgs), len(newmsgs)))
    if 0 != len(newmsgs):
        echo (term.bright_green)
        echo ('\r\n  --> Read new private messages? [yna]   <--' + '\b'*5)
        echo (term.normal)
        while True:
            k = getch()
            if str(k).lower() == 'y':
                #savescreen = getsession().buffer['resume'].getvalue()
                gosub('msgreader', [msg for msg in newmsgs])
                #echo (savescreen) # restore screen
                break
            elif str(k).lower() == 'a':
                #savescreen = getsession().buffer['resume'].getvalue()
                gosub('msgreader', [msg for msg in privmsgs])
                #echo (savescreen) # restore screen
                break
            elif str(k).lower() == 'n':
                break

    # check for new public messages
    echo ('\r\n\r\n  Checking for public messages...')

    pubmsgs = msgbase.listpublicmsgs()
    newmsgs = [msg for msg in pubmsgs if not getsession().handle in getmsg(msg).read]

    echo ('%s messages, %s new\r\n' % (len(pubmsgs), len(newmsgs)))
    if len(newmsgs):
        echo (term.bright_green)
        echo ('\r\nRead new public messages? [yna] ')
        echo (term.normal ())
        while True:
            k = getch()
            if k.lower() == 'y':
                #savescreen = getsession().buffer['resume'].getvalue()
                gosub('msgreader', [msg for msg in newmsgs])
                #echo (savescreen) # restore screen
                break
            elif k.lower() == 'a':
                #savescreen = self.buffer['resume'].getvalue()
                gosub('msgreader', [msg for msg in pubmsgs])
                #echo (savescreen) # restore screen
                break
            elif k.lower() == 'n':
                break
