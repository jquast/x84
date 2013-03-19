""" Password reset script for x/84, http://github.com/jquast/x84 """

from x84.bbs import getsession, getterminal, list_users, echo, getch, ini
from x84.bbs import LineEditor, get_user

from x84.default.nua import set_password
import logging
import smtplib
import base64
import os
from email.mime.text import MIMEText


def main(handle):
    """ Main procedure. """
    # pylint: disable=R0914,R0915,R0911
    #         Too many local variables
    #         Too many statements
    #         Too many return statements
    # by request from midget; a password reset form
    session, term = getsession(), getterminal()
    session.activity = 'resetting password for %s' % (handle,)
    user = get_user(handle)
    logger = logging.getLogger()

    prompt_email = u'\r\n\r\nENtER E-MAil fOR %r: '
    msg_nfound = u'\r\n\r\n%r NOt fOUNd iN USERbASE.'
    msg_cancelled = u'\r\n CANCEllEd.'
    msg_wrong = u'\r\n\r\nWRONG'
    msg_mailsubj = u'passkey for %s' % (ini.CFG.get('system', 'bbsname'))
    msg_mailbody = u'Your passkey is %r'
    msg_mailfrom = ini.CFG.get('system', 'mail_addr')
    msg_sent = u'\r\n\r\nPASSkEY hAS bEEN SENt tO %s.'
    prompt_passkey = u'\r\n\r\nENtER PASSkEY: '
    msg_verified = u'\r\n\r\nYOU hAVE bEEN VERifiEd.'

    echo(term.normal)
    if not handle in list_users():
        echo(term.bold_red(msg_nfound))
        getch()
        return False

    width = ini.CFG.getint('nua', 'max_email')
    email = None
    tries = 0
    while True:
        tries += 1
        if tries > 5:
            logger.warn('%r email retries exceeded', handle)
            return False
        echo(prompt_email % (handle,))
        try_email = LineEditor(width).read()
        if try_email is None or 0 == len(try_email):
            echo(term.normal + msg_cancelled)
            return False

        # fetch user record email
        email = get_user(handle).email
        if email is None or 0 == len(email):
            logger.warn('%r missing email address, cannot send', handle)
            echo(term.bold_red(msg_wrong))

        elif email.lower() != try_email.lower():
            logger.warn('%r failed email %r (try: %r)', handle,
                        email, try_email)
            echo(term.bold_red(msg_wrong))

        else:
            logger.info('%r requests password reset to %r', handle, email)
            break

    # generate a 'passkey' and e-mail out of band, and request input
    passkey = base64.encodestring(
        os.urandom(ini.CFG.getint('nua', 'max_pass'))
    )[:ini.CFG.getint('nua', 'max_pass')]
    msg = MIMEText(msg_mailbody % (passkey,))
    msg['From'] = msg_mailfrom
    msg['To'] = email
    msg['Subject'] = msg_mailsubj
    # pylint: disable=W0703
    #         Catching too general exception Exception
    err = None
    try:
        smtp = smtplib.SMTP(ini.CFG.get('system', 'mail_smtphost'))
        smtp.sendmail(msg_mailfrom, [email], msg.as_string())
        smtp.quit()
    except Exception as err:
        logger.exception(err)
        echo('u\r\n\r\n' + term.bold_red(str(err)) + u'\r\n')
        getch(2)
        return False

    echo(msg_sent % (email,))
    width = len(passkey)
    email = None
    tries = 0
    while True:
        tries += 1
        if tries > 5:
            logger.warn("passkey retries exceeded for user '%s'", handle)
            return False

        echo(term.normal + u'\r\n\r\n')
        echo(prompt_passkey)
        try_passkey = LineEditor(width).read()
        if try_passkey is None or 0 == len(try_passkey):
            echo(term.normal + msg_cancelled)
            logger.warn("cancelled passkey for user '%s'", handle)
            return False

        if passkey == try_passkey:
            echo(term.bold_green(msg_verified))
            echo(u'\r\n\r\n')
            break
        logger.warn("failed passkey for user '%s': '%s', tried '%s')",
                    handle, passkey, try_passkey)
        echo(term.bold_red(msg_wrong))

    set_password(user)
    user.save()
    return True
