""" top-level scripting module for x/84. """
# local side-effect producing imports
# (encodings such as 'cp437_art' become registered)
__import__('encodings.aliases')
__import__('x84.encodings')

# local/exported at top-level 'from bbs import ...'
from x84.bbs.ansiwin import AnsiWindow
from x84.bbs.dbproxy import DBProxy
from x84.bbs.door import Door, DOSDoor, Dropfile
from x84.bbs.editor import LineEditor, ScrollingEditor
from x84.bbs.exception import Disconnected, Goto
from x84.bbs.ini import get_ini
from x84.bbs.lightbar import Lightbar
from x84.bbs.modem import send_modem, recv_modem
from x84.bbs.msgbase import list_msgs, get_msg, list_tags, Msg, list_privmsgs
from x84.bbs.output import (echo, timeago, encode_pipe, decode_pipe,
                            syncterm_setfont, showart, ropen,
                            from_cp437,  # deprecated in v2.0
                            )
from x84.bbs.pager import Pager
from x84.bbs.script_def import Script
from x84.bbs.selector import Selector
from x84.bbs.session import (getsession, getterminal,
                             goto, disconnect, gosub,
                             getch,      # deprecated in v2.1
                             )
from x84.bbs.userbase import list_users, get_user, find_user, User, Group

# the scripting API is generally defined by this __all__ attribute, but
# the real purpose of __all__ is defining what gets placed into a caller's
# namespace when using statement `from x84.bbs import *`
__all__ = ('list_users', 'get_user', 'find_user', 'User', 'Group', 'list_msgs',
           'get_msg', 'list_tags', 'Msg', 'LineEditor', 'ScrollingEditor',
           'echo', 'timeago', 'AnsiWindow', 'Selector', 'Disconnected', 'Goto',
           'Lightbar', 'from_cp437', 'DBProxy', 'Pager', 'Door', 'DOSDoor',
           'goto', 'disconnect', 'getsession', 'getterminal', 'getch', 'gosub',
           'ropen', 'showart', 'Dropfile', 'encode_pipe',
           'decode_pipe', 'syncterm_setfont', 'get_ini', 'send_modem',
           'recv_modem', 'Script', 'list_privmsgs',
           )
