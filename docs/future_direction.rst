=================
Future Directions
=================

basic v3.0 roadmap:

* python3 using async i/o
* windows support, requires ansi.sys support emulation for PDCurses in blessed
* ftp, ftps, fxp support
* modeling (using 'schematics' project) for userbase, messagebase, etc. 
* support for agoranet, zeronet, etc. messaging networks
* a classic "waiting for callers" screen and /dev/tty-line support.
  this was supported in previous versions, but dropped due to blessed's
  requirements of requiring a unique process for each terminal.
* start as daemon (-d)
* Convert messaging to data modeling format (schematics?) and rfc-compliant
  mail messaging.
* cron-like scheduling of scripts (fe., msgpoll.py)

Feel free to contribute ideas as a github issue.
