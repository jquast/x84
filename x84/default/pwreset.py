# -*- coding: utf-8 -*-
""" Password reset script for x/84. """
from __future__ import division

import string
import random

from x84.bbs import getsession, getterminal
from x84.bbs import echo, LineEditor
from x84.bbs import get_ini, find_user, get_user
from common import display_banner

import logging
import smtplib
import base64
import os
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

here = os.path.dirname(__file__)

#: maximum length of user handles
username_max_length = get_ini(section='nua',
                              key='max_user',
                              getter='getint'
                              ) or 10

#: maximum length of password
password_max_length = get_ini(section='nua',
                              key='max_pass',
                              getter='getint'
                              ) or 15

#: maximum length of email address
email_max_length = get_ini(section='nua',
                           key='max_email',
                           getter='getint'
                           ) or 40

#: smtp host for mail delivery
mail_smtphost = get_ini(section='system', key='mail_smtphost'
                        ) or 'localhost'

#: body of password reset message
msg_mailbody = (u'A password reset has been requested on {bbsname} '
                u'from {session.sid!r} by matching your user handle '
                u'{user.handle!r} and e-mail address.\r\n\r\n'
                u'Your password reset key is {passkey!r}')

msg_mailsubj = u'Passkey token for {bbsname}'

msg_mailfrom = get_ini(section='system',
                       key='mail_addr'
                       ) or 'sysop@localhost.localdomain'

#: name of bbs
system_bbsname = get_ini(section='system',
                         key='bbsname'
                         ) or 'Unnamed'

#: banner art file
art_file = os.path.join(here, 'art', 'pwreset.asc')

#: primary color (highlight)
color_primary = 'red'

#: secondary color (lowlight)
color_secondary = 'bold_black'

#: maximum attempts for passkey authentication
passkey_max_attempts = 5

#: password hidden character
hidden_char = u'\u00f7'

#: positions next prompt 40 pixels minus center of screen
fixate_next = lambda term: (
    u'\r\n\r\n' + term.move_x(max(0, (term.width // 2) - 40)))


def display_banner_animation(banner_text):
    """
    Display animation of "cracking" the banner text.

    This is inspired by all those movies.
    """
    session, term = getsession(), getterminal()
    highlight = getattr(term, color_primary)
    lowlight = getattr(term, color_secondary)
    animation_length = len(banner_text)
    animation_speed = 0.1

    def get_garbage():
        # get some random "cracking" strings
        txt = list(string.printable)[:len(banner_text)]
        random.shuffle(txt)
        return txt

    get_x = lambda: (
        # get x-position of banner (center)
        (term.width // 2) - (len(banner_text) // 2))

    def display_header(xpos, banner_text):
        x_top_left = xpos - 1
        x_bot_right = xpos + (len(banner_text) - 5)
        return u'\r\n'.join((
            u'{xpos}{txt}'.format(xpos=term.move_x(x_top_left),
                                  txt=lowlight(u'┬─────')),
            u'',
            u'{xpos}{txt}'.format(xpos=term.move_x(x_bot_right),
                                  txt=lowlight(u'─────┴')),
        ))

    def decorate_guess(guess, actual):
        # return string where matching letters are highlighted
        attr = None
        rstr = u''
        for idx, ch_guess in enumerate(guess):
            # optimized attribute draws
            if ch_guess == actual[idx]:
                if attr != highlight:
                    attr = highlight
                    rstr += term.normal + attr
            else:
                if attr != lowlight:
                    attr = lowlight
                    rstr += term.normal + attr
            rstr += ch_guess
        return rstr

    def merge_garbage(prior_guess, garbage, actual):
        # return string with new garbage mixed in,
        # except where already matching
        next_guess = garbage[:]
        for idx, garbage_item in enumerate(garbage):
            if prior_guess[idx] == actual[idx]:
                next_guess[idx] = actual[idx]
            else:
                next_guess[idx] = garbage_item
        return next_guess

    def make_match(guess, actual):
        next_guess = guess[:]
        indicies = range(len(actual))
        random.shuffle(indicies)
        for idx in indicies:
            if next_guess[idx] != actual[idx]:
                next_guess[idx] = actual[idx]
                break
        return next_guess

    xpos = get_x()

    # display header,
    echo(display_header(xpos, banner_text))

    # move-to banner animation row
    echo(term.move_up())

    guess = get_garbage()
    for _ in range(0, animation_length):
        # check for screen resize
        if session.poll_event('refresh'):
            # remove artifacts, get new center
            echo(term.move_x(0) + term.clear_eol)
            xpos = get_x()

        echo(term.move_x(xpos))
        echo(decorate_guess(guess=guess, actual=banner_text))
        echo(term.clear_eol)

        if guess == banner_text:
            # "cracked"
            break

        if term.inkey(timeout=animation_speed):
            # user canceled animation
            break

        # mix in new garbage
        guess = merge_garbage(prior_guess=guess,
                              garbage=get_garbage(),
                              actual=banner_text)

        # ensure at least one new index is guessed
        guess = make_match(guess=guess,
                           actual=banner_text)

    # end of animation
    echo(term.move_x(xpos))
    echo(highlight(banner_text))
    echo(term.move_x(0) + (term.move_down * 2))


def prompt_input(term, key, **kwargs):
    """ Prompt for user input. """
    sep_ok = getattr(term, color_secondary)(u'::')
    sep_bad = getattr(term, color_primary)(u'::')
    colors = {'highlight': getattr(term, color_primary)}

    echo(fixate_next(term))
    echo(u'{sep} {key:>18}: '.format(sep=sep_ok, key=key))
    entry = LineEditor(colors=colors, **kwargs).read() or u''
    if not entry.strip():
        echo(fixate_next(term))
        echo(u'{sep} Canceled !\r\n'.format(sep=sep_bad))
        log.debug('Password reset canceled at prompt key={0}.'.format(key))
        return u''

    return entry


def matches_email(handle, email):
    """ Return User record for handle if it matches email. """
    matching_handle = find_user(handle)
    user = matching_handle and get_user(matching_handle)
    if not user:
        log.debug('password reset failed, no such user {0} for email {1}.'
                  .format(handle, email))
        return False
    elif not user.email.strip():
        log.debug('password reset failed, user {0} has no email on file.'
                  .format(handle))
        return False
    elif email.lower() != user.email.lower():
        log.debug('pasword reset failed, email mismatch: {0} != {1}.'
                  .format(email, user.email))
        return False

    # success !
    return user


def send_passkey(user):
    """ Send passkey token to user by e-mail. """
    session = getsession()
    passkey = base64.encodestring(os.urandom(50))[:password_max_length]

    email_msg = MIMEText(msg_mailbody.format(bbsname=system_bbsname,
                                             session=session,
                                             user=user,
                                             passkey=passkey))
    email_msg['From'] = msg_mailfrom
    email_msg['To'] = user.email
    email_msg['Subject'] = msg_mailsubj.format(bbsname=system_bbsname)

    try:
        smtp = smtplib.SMTP(mail_smtphost)
        smtp.sendmail(msg_mailfrom, [user.email], email_msg.as_string())
        smtp.quit()
    except Exception as err:
        log.exception(err)
        echo(u'{0}'.format(err))
        return False

    log.info(u'Password reset token delivered '
             u'to address {0!r} for user {1!r}.'
             .format(user.email, user.handle))
    return passkey


def do_reset(term, handle, email=u''):
    """ Password reset by e-mail loop. """
    sep_ok = getattr(term, color_secondary)(u'::')
    sep_bad = getattr(term, color_primary)(u'::')
    email = u''

    for _ in range(passkey_max_attempts):
        handle = prompt_input(term=term,
                              key='Username',
                              content=handle or u'',
                              width=username_max_length)

        if not handle:
            # canceled
            return False

        email = prompt_input(term=term,
                             key='E-mail',
                             content=email or u'',
                             width=email_max_length)
        if not email:
            # canceled
            return False

        user = matches_email(handle, email)
        if not user:
            echo(fixate_next(term))
            echo(u'{0} Address is incorrect !'.format(sep_bad))
            # try e-mail address again
            continue

        echo(fixate_next(term))
        passkey = send_passkey(user)
        if not passkey:
            # failed to send e-mail
            term.inkey(1)
            echo(u'\r\n\r\n')
            return False

        echo(u'{0} E-mail successfully delivered !'.format(sep_ok))

        for _ in range(passkey_max_attempts):
            try_passkey = prompt_input(term=term,
                                       key='Passkey',
                                       width=password_max_length)

            if not try_passkey:
                # canceled
                return False

            if passkey.strip() != try_passkey.strip():
                # passkey does not match
                echo(fixate_next(term))
                echo(u'{0} Passkey does not verify !'.format(sep_bad))
                # try passkey again
                continue

            new_password = prompt_input(term=term,
                                        key='Password',
                                        hidden=hidden_char,
                                        width=password_max_length)
            if not new_password:
                # canceled
                return False

            user.password = new_password
            user.save()
            log.debug('password reset successful for user {0!r}.'
                      .format(user.handle))
            echo(fixate_next(term))
            echo(u'{0} Password reset successful !'.format(sep_ok))
            return True

        echo(fixate_next(term))
        echo(u'{0} Too many authentication attempts.'.format(sep_bad))

    echo(fixate_next(term))
    echo(u'{0} Too many authentication attempts.'.format(sep_bad))


def main(handle=None):
    """
    Main procedure.
    """
    session, term = getsession(), getterminal()
    session.activity = u'resetting password'

    display_banner(art_file)

    # mix animation into art
    echo(term.move_up() * 5)

    # display banner animation
    display_banner_animation(banner_text=u'reset account password')

    return do_reset(term, handle)
