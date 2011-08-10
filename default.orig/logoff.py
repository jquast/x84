"""
 Logoff module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: logoff.py,v 1.3 2008/05/10 08:27:25 dingo Exp $

 This modulde demonstrates the bps option for showfile().
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

deps = ['bbs']

def main():
  gosub('comment')
  session.activity = 'Logging Off!'

  echo (charset() + cls())
  showfile ('ans/shd/*.ans', bps=19200)
  readkey (2)
  echo ( cls() + \
  'Try some of these other great boards!\r\n' \
  '  htc.zapto.org              The Haunted Chapel          open access\r\n' \
  '  +o MercyFul Fate           C++/BSD      (enthral )       closed source\r\n\r\n' \
    \
  '  velvet.ath.cx              The Shack                   open access\r\n' \
  '  +o Kreator/Coz             C?/BSD       (        )       closed source\r\n\r\n' \
    \
  '  centre.segfault.net        The Centre                  open access Apr 2008\r\n' \
  '  +o tombin                  perl/linux   (        )       closed source\r\n\r\n' \
    \
  '  xxxxxxxx.xxx               Psylent development         closed access\r\n' \
  '  +o sinister x              .NET/win32NT (psylent )       snapshot available\r\n\r\n' \
    \
  '  bld.ph4.se                 Blood Island                open access\r\n' \
  '  +o hellbeard               python/linux (prsv    )       open source\r\n\r\n' \
    \
  '  xxxxxxxx.xxx               prsv development            closed access\r\n' \
  '  +o jojo                    python/linux (prsv    )       open source\r\n\r\n' \
    \
  '  graveyardbbs.kicks-ass.net The Graveyard               open access\r\n' \
  '  +o The Reaper              pascal/win32 (renegade)       what the hell!\r\n\r\n' \
  )
  readkey (10)
  disconnect ()
