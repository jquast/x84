"""
 New user account script for X/84, http://1984.ws

 Simply create a new User() instance and set the most minimum values,
 such as handle and password, then call the .save() method to commit
 this record.
"""

# input area (y, x)
loc_user   = (12, 20)
loc_origin = (14, 20)
loc_pass   = (16, 20)
loc_email  = (18, 20)
loc_state  = (20, 10)
loc_prompt = (23, 35)
# grr, (x, y) ?
loc_yesno  = (62, 23) #23, 62)

def main (handle):
    import os
    if handle.lower() in ('new',):
        handle = u''
    location, hint = u'', u''
    password, verify, = u'', u''
    session = getsession()
    terminal = getterminal()

    def warning(msg):
        " Display warning to user with a dynamic pause "
        cpsec =  10.0
        min_sec = 3
        split_loc = 3
        warning_msg = u''.join((
            terminal.clear_eol,
            terminal.normal, terminal.red, msg[:-split_loc],
            terminal.normal, msg[-split_loc:],
            terminal.bright_black, u'!'))
        echo (warning_msg)
        inkey = getch(max(min_sec,float(len(msg))/cpsec))
        echo (terminal.clear_bol)
        return inkey

    session.activity = u'New User Application'
    echo (terminal.clear + terminal.normal)
    showfile ('art/newuser.asc')
    echo ( u'New User Application'.center (terminal.width-1) + u'\r\n')

    while True:
        user_ok = origin_ok = pass_ok = level = 0
        while not (user_ok):
            echo (terminal.move (*loc_user))
            echo (terminal.clear_eol + terminal.normal)
            echo (u'username: ')
            handle = readline (int(ini.cfg.get('nua', 'max_user')), handle)
            echo (terminal.move (*loc_user))
            if not handle:
                inkey = warning(u'Enter an alias, Press Ctrl+X to cancel')
                if inkey == chr(24):
                    return
            elif finduser (handle):
                warning (u'User exists')
            elif (handle == u''
                    or len(handle) < int(ini.cfg.get('nua', 'min_user'))):
                warning (u'Too short! (%s)' % ini.cfg.get('nua', 'min_user'))
            elif (handle.lower() in ini.cfg.get('nua',
                'invalid_handles').split()):
                warning (u'Illegal username')
            elif os.path.sep in handle:
                # handle is often used for filenames, like tty recordings,
                # so avoid allowing usernames with '/' inside the nickname
                warning (u'Illegal username')
            elif ':' in handle:
                # hrm,
                warning (u'Illegal username')
            else:
                user_ok = True

        while not (origin_ok):
            echo (terminal.move (*loc_origin))
            echo (terminal.clear_eol + terminal.normal)
            echo (u'origin: ')
            location = readline (int(ini.cfg.get('nua', 'max_origin')), location)
            echo (terminal.move (*loc_origin))
            if location == u'':
                inkey = warning(u'Enter a location, Press Ctrl+X to cancel')
                if inkey == chr(24):
                    return
                echo (terminal.clear_eol)
            else:
                origin_ok = True

        while not (pass_ok):
            echo (terminal.move(*loc_pass))
            echo (terminal.clear_eol + terminal.normal)
            echo (u'password: ')
            password = readline (int(ini.cfg.get('nua', 'max_pass')), hidden='x')
            echo (terminal.move(*loc_pass))
            if len(password) < 4:
                # fail if password too short
                echo (terminal.move (*loc_email))
                inkey = warning(u'too short, Press Ctrl+X to cancel')
                if inkey == chr(24):
                    return
                echo (terminal.clear_eol)
            else:
                # verify
                echo (terminal.clear_eol + terminal.normal)
                echo (u'   again: ')
                verify = readline (int(ini.cfg.get('nua', 'max_pass')), hidden='z')
                echo (terminal.move(*loc_pass))
                if password != verify:
                    inkey = warning (u'verify must match, Press Ctrl+X to cancel')
                    if inkey  == chr(24):
                        return
                    echo (terminal.clear_eol)
                else:
                    break

        # this is a joke?
        while (level < 2):
            echo (terminal.move(*loc_email))
            # email loop
            echo (terminal.clear_eol + terminal.normal)
            echo (u'e-mail (optional): ')
            hint= readline (int(ini.cfg.get('nua', 'max_email')))
            echo (terminal.move(*loc_email))
            # TODO regexp
            if not len(hint):
                level = 2
                break # no e-mail
            for ch in hint:
                # must have @, level 1
                if ch == u'@':
                    level = 1
                # must have '.' following @, level 2
                if level == 1 and ch == u'.':
                    level = 2
                    break
            if level == 2:
                # email is valid, break out
                break

            # allow user to opt-out of e-mail
            echo (terminal.move (*loc_state))
            inkey = warning(u'invalid, Ctrl+O to Opt out')
            echo (terminal.move (*loc_state))
            if inkey == chr(15):
                echo (terminal.clear_eol + terminal.normal)
                echo (u'make your statement, then: ')
                hint = readline (int(ini.cfg.get('nua', 'max_email')))
                if not hint:
                    return
                break

        echo (terminal.move (*loc_prompt))
        echo (terminal.clear_eol + terminal.normal)
        echo (u'   Everything cool?')

        lr = YesNoClass(loc_yesno)
        lr.left ()
        lr.run()
        if lr.isleft():
            # handle, password, location, hint
            # XXX decode necessary now?
            u = User (handle=handle.decode('utf-8'),
                password=password.decode('utf-8'),
                location=location.decode('utf-8'),
                hint=hint.decode('utf-8'))
            u.save ()
            goto (ini.cfg.get('matrix', 'topscript'), u.handle)
