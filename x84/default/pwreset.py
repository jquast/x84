"""
Password reset script for x/84, http://github.com/jquast/x84
"""

from x84.bbs import getsession, getterminal, list_users, echo, getch, ini
from x84.bbs import LineEditor, get_user

import logging
import smtplib
import base64
import os
from email.mime.text import MIMEText

def main(handle):
    # by request from midget; a password reset form
    session, term = getsession(), getterminal()
    user = get_user(handle)
    logger = logging.getLogger()
    prompt_email = u'ENtER E-MAil fOR %r: '
    msg_nfound = u'\r\n%r NOt fOUNd iN USERbASE.\r\n'
    msg_cancelled = u'\r\n CANCEllEd.\r\n'
    msg_wrong = u'\r\nWRONG\r\n'
    msg_mailsubj = u'passkey for %s' % (ini.CFG.get('system', 'bbsname'))
    msg_mailbody = u'Your passkey is %r'
    msg_mailfrom = ini.CFG.get('system', 'mail_addr')
    msg_sent = u'PASSkEY hAS bEEN SENt tO %s.'
    prompt_passkey = u'ENtER PASSkEY: '
    msg_verified = u'YOU hAVE bEEN VERifiEd.'

    if not handle in list_users():
        echo (term.bold_red(msg_nfound))
        getch ()
        return

    width = ini.CFG.getint('nua', 'max_email')
    email = None
    tries = 0
    while True:
        tries += 1
        if tries > 5:
            logger.warn ('%r email retries exceeded', handle)
            return
        echo (term.normal + u'\r\n\r\n')
        echo (prompt_email % (handle,))
        try_email = LineEditor(width).read()
        if try_email is None or 0 == len(try_email):
            echo (term.normal + msg_cancelled)
            return

        # fetch user record email
        email = get_user(handle).email
        if email is None or 0 == len(email):
            logger.warn ('%r missing email address, cannot send', handle)
            echo (term.bold_red(msg_wrong))

        elif email.lower() != try_email.lower():
            logger.warn ('%r failed email %r (try: %r)', handle,
                    email, try_email)
            echo (term.bold_red(msg_wrong))

        else:
            logger.info ('%r requests password reset to %r', handle, email)
            break

    # generate a 'passkey' and e-mail out of band, and request input
    passkey = base64.encodestring(
            os.urandom(ini.CFG.getint('nua', 'max_pass'))
            )[:ini.CFG.getint('nua', 'max_pass')]
    msg = MIMEText(msg_mailbody % (passkey,))
    msg['From'] = msg_mailfrom
    msg['To'] = email
    msg['Subject'] = msg_mailsubj
    smtp = smtplib.SMTP(ini.CFG.get('system', 'mail_smtphost'))
    smtp.sendmail (msg_mailfrom, [email], msg.as_string())
    smtp.quit ()

    echo ('\r\n\r\n' + msg_sent % (email,) + '\r\n')
    echo ('\r\n\r\n')

    width = len(passkey)
    email = None
    tries = 0
    while True:
        tries += 1
        if tries > 5:
            logger.warn ('%r passkey retries exceeded', handle)
            return

        echo (term.normal + u'\r\n\r\n')
        echo (prompt_passkey)
        try_passkey = LineEditor(width).read()
        if try_passkey is None or 0 == len(try_passkey):
            echo (term.normal + msg_cancelled)
            logger.warn ('%r cancelled passkey', handle)
            return

        if passkey == try_passkey:
            echo (term.bold_green(msg_verified))
            break
        logger.warn ('%r failed passkey %r (try: %r)', handle,
                passkey, try_passkey)
        echo (term.bold_red(msg_wrong))

    import nua
    nua.set_password (user)
    return True
