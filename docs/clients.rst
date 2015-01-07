==================
Compatible Clients
==================

Any UTF-8 client is compatible. For Apple systems, *Andale Mono* works wonderfully.

PuTTy
=====

Under preference item *Window -> Translation*, option *Remote character set*, change *iso8859-1* to *UTF-8*.

iTerm
=====

Menu item *iTerm -> Preferences*, section *Profiles*, select tab *Text*, chose *Andale Mono* font.

Terminal.app
============
Menu item *Terminal => Preferences*, chose profile *Pro*, select Font *Andale Mono*, and enable *use bright colors for bold text*.

uxterm
======

Or other utf-8 rxvt and xterm variants: urxvt, dtterm.

Non-unicode
===========

Other than UTF-8, only IBM CP437 encoding is supported. Any telnet client with CP437 font is supported.

Examples of these include PuTTy, SyncTerm, mtel, netrunner, linux/bsd console + linux/bsd telnet.

Some non-DOS terminal emulators may require installing a fontset, such as *Terminus_* to provide CP437 art.

TCP Encryption
==============

Telnet is not a secure protocol.  This implementation of x/84 is without any encryption. It is not secure from network eavesdropping. SSH is supported and works perfectly fine if eavesdropping is a concern.

.. _Terminus: http://terminus-font.sourceforge.net/
