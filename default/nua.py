"""
 New user account script for x/84, https://github.com/jquast/x84
"""

def warning(msg, cpsec=10.0, min_sec=3.0, split_loc=3):
    """
    Display a 2-tone warning to user with a dynamic pause
    """
    term = getterminal()
    echo (u''.join((term.clear_eol, term.normal, u'\r\n\r\n',
        term.bold_red, msg[:-split_loc], term.normal, msg[-split_loc:],
        term.bold_black, u'!')))
    inp = getch(max(min_sec, float(len(msg)) / cpsec))
    return inp

def set_handle(user):
    """
    Prompt for a user.handle, minumum length.
    """
    import os.path # os.path.sep not allowed in nicks
    term = getterminal ()
    prompt_handle = u'username: '
    msg_empty = u'ENtER AN AliAS'
    msg_exists = u'USER EXiStS.'
    msg_tooshort = u'TOO ShORt, MUSt bE At lEASt %s.'
    msg_invalid = u'IllEGAl USERNAME'
    width = ini.CFG.getint('nua', 'max_user')
    min_user = ini.CFG.getint('nua', 'min_user')
    invalid_nicks = ini.CFG.get('nua', 'invalid_handles').split()
    while True:
        echo (u'\r\n\r\n' + term.clear_eol + term.normal + prompt_handle)
        user.handle = LineEditor (width, user.handle).read()
        if user.handle == u'' or user.handle is None:
            warning(msg_empty)
        elif find_user (user.handle):
            warning (msg_exists)
        elif len(user.handle) < min_user:
            warning (msg_tooshort % min_user)
        elif ((user.handle.lower() in invalid_nicks)
                or os.path.sep in user.handle):
            warning (msg_invalid)
        else:
            return

def set_location(user):
    """
    Prompt for and set user.location, may be empty
    """
    term = getterminal()
    prompt_location = u'origin (optional): '
    width = ini.CFG.getint('nua', 'max_location')
    echo (u'\r\n\r\n' + term.clear_eol + term.normal + prompt_location)
    user.location = LineEditor (width, user.location).read()
    if user.location is None:
        user.location = u''

def set_email(user):
    """
    Prompt for and set user.email, may be empty
    """
    term = getterminal()
    prompt_email = u'e-mail (optional): '
    width = ini.CFG.getint('nua', 'max_email')
    echo (u'\r\n\r\n' + term.clear_eol + term.normal + prompt_email)
    user.email = LineEditor (width, user.email).read()
    if user.email is None:
        user.email = u''

def set_password(user):
    """
    Prompt for user.password, minimum length.
    """
    term = getterminal ()
    prompt_password = u'password: '
    prompt_verify = u'   again: '
    msg_empty = u'ENtER A PASSWORd!'
    msg_tooshort = u'TOO ShORt, MUSt bE At lEASt %s.'
    msg_unmatched = u'VERifY MUSt MAtCH!'
    width = ini.CFG.getint('nua', 'max_pass')
    min_pass = ini.CFG.getint('nua', 'min_pass')
    while True:
        echo (u'\r\n\r\n' + term.clear_eol + term.normal + prompt_password)
        le = LineEditor (width)
        le.hidden = 'x'
        password = le.read()
        if password == u'' or password is None:
            warning(msg_empty)
        elif len(password) < min_pass:
            warning (msg_tooshort % min_pass)
        else:
            echo (u'\r\n\r\n' + term.clear_eol + term.normal + prompt_verify)
            le = LineEditor (width)
            le.hidden = 'x'
            verify = le.read()
            if password != verify:
                warning (msg_unmatched)
                continue
            user.password = password
            return

def prompt_ok():
    """
    Prompt user to continue, True if they select yes.
    """
    session, term = getsession(), getterminal()
    prompt_confirm = u'EVERYthiNG lOOk Ok ?'
    prompt_continue = u'YES (CONtiNUE)'
    prompt_chg = u'NO! (ChANGE)'
    def prompt_ok_dumb(user):
        echo ('\r\n\r\n%s\r\n' % (prompt_confirm,))
        echo ('1 - %s\r\n' % (prompt_continue,))
        echo ('2 - %s\r\n\r\n' % (prompt_chg,))
        echo ('select (1, 2) --> ')
        while True:
            ch = getch()
            if ch == u'1':
                return True
            elif ch == u'2':
                return False
    if session.env.get('TERM') == 'unknown':
        return prompt_ok_dumb()
    sel = Selector(yloc=term.height - 1, xloc=5,
            width=term.width - 10, left=prompt_continue, right=prompt_chg)
    echo (term.normal)
    echo (term.move(term.height - 2, 0) + term.clear_eol)
    echo (prompt_confirm.center(term.width-1) + '\r\n')
    echo (term.clear_eol + sel.refresh())
    while True:
        echo (sel.process_keystroke(getch()))
        if sel.selected:
            return True if sel.selection == prompt_continue else False

def main (handle=u''):
    session, term = getsession(), getterminal()
    session.activity = u'Applying for an account'
    artfile = u'art/newuser.asc'
    msg_header = u'NEW USER APPliCAtiON'
    newcmds = ini.CFG.get('matrix', 'newcmds').split()
    topscript = ini.CFG.get('matrix', 'topscript')

    # display art and msg_header as banner
    echo (term.clear + term.normal + showcp437(artfile))
    echo (u'\r\n\r\n' + term.reverse + msg_header.center (term.width))

    # create new user record for manipulation
    user = User(handle if handle.lower() not in newcmds else u'')
    while True:
        set_handle (user)
        set_location (user)
        set_email (user)
        set_password (user)
        if prompt_ok ():
            user.save ()
            goto (topscript)
