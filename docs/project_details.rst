Compatible Clients
==================

Any UTF-8 client is compatible. For Apple systems, *Andale Mono* works wonderfully.

PuTTy
-----

Under preference item *Window -> Translation*, option *Remote character set*, change *iso8859-1* to *UTF-8*.

iTerm
-----

Menu item *iTerm -> Preferences*, section *Profiles*, select tab *Text*, chose *Andale Mono* font.

Terminal.app
------------
Menu item *Terminal -> Preferences*, chose profile *Pro*, select Font *Andale Mono*, and enable *use bright colors for bold text*.

uxterm
------

Or other utf-8 rxvt and xterm variants: urxvt, dtterm.

Non-unicode
-----------

Other than UTF-8, only IBM CP437 encoding is supported. Any telnet client with CP437 font is supported.

Examples of these include PuTTy, SyncTerm, mtel, netrunner, linux/bsd console + linux/bsd telnet.

Some non-DOS terminal emulators may require installing a fontset, such as *Terminus_* to provide CP437 art.

TCP Encryption
--------------

Telnet is not a secure protocol.  This implementation of x/84 is without any encryption. It is not secure from network eavesdropping. SSH is supported and works perfectly fine if eavesdropping is a concern.

.. _Terminus: http://terminus-font.sourceforge.net/


Binding to port 23
==================

x/84 does not require privileged access, and its basic configuration binds to port 6023 for telnet and 6022 for ssh. Multi-user systems do not typically allow non-root users to bind to port 23 or 22.  Below are various techniques for allowing it.

Alternatively, you can always use port forwarding on a NAT firewall.

Linux
-----

using privbind_, run the BBS as user 'nobody', group 'nogroup'::

  sudo privbind -u nobody -g nogroup x84

Solaris 10
----------

grant net_privaddr privilege to user 'bbs'::

  usermod -K defaultpriv=basic,net_privaddr bbs

BSD
---

redirection using pf(4)::

  pass in on egress inet from any to any port telnet rdr-to 192.168.1.11 port 6023

Other
-----

Using socat_, listen on 192.168.1.11 and for each connection, fork as 'nobody', and pipe the connection to 127.0.0.1 port 6023::

  sudo socat -d -d -lmlocal2 TCP4-LISTEN:23,bind=192.168.1.11,su=nobody,fork,reuseaddr TCP4:127.0.0.1:6023

This has the disadvantage that x84 is unable to identify the originating IP.

.. _privbind: http://sourceforge.net/projects/privbind/
.. _socat: http://www.dest-unreach.org/socat/


Other Telnet BBS Systems
========================

Listed here is software known in the "bbs-scene" as still being actively used, in descending order of their estimated popularity.

* mystic_: Pascal, create a sourceforge account to access source code.
* synchronet_: C formerly commercial, now open source.
* daydream_: C open source.
* enthral_: C++ open source.

Many more systems can be found at List_of_BBS_software_

How x/84 compares
-----------------

It might best to compare x/84 with the most popularly used surviving BBS systems, mainly: mystic_, synchronet_, and daydream_.

*Process Management*

  - All other systems are single process: executed as a "login shell" by xinet.d or similar, they depend on additional 3rd-party systems and distribution packages for telnet or ssh support.
  - x/84 on the other hand, is a single process that manages the telnet, ssh, sftp, web, and rlogin server.  This means 0-configuration to go online, only toggling the availability of any given service -- it requires no special user accounts or external distribution dependencies other than python and python packages.  This tight integration allows one login by ssh or sftp with your bbs user account and public key and communicate window-size change events.
  - as a dynamic language, it also allows one to rapidly develop on much of the system without compilation or publishing layer -- simply login again to see the new changes afresh without restarting the server, and without a compilation step.


*Scripting Layer*

  - All other systems are written in C or Pascal, published in binary form, providing a limited subset of functionality through a scripting layer in an entirely different language, such as a particular dialect of javascript, python, perl, or pascal.
  - x/84 is python throughout -- you may extend the engine layer to provide new features in the same language and with full access in the scripting layer without providing any stubs, function exports, or facilitating modules.  The same methods used in the engine for session and user management are available in the scripting layer.

*Customization*

  - Most systems take an approach of providing a proprietary layer of customization: special menu files with codes for navigating between other menus and scripts, or displaying artfiles with special codes for displaying dynamic data such as a login name.
  - x/84 customization is done only by python scripting.  Making a menu is simply writing a script to do so.  One may simply echo out the contents of an artfile, move the cursor to the desired location, and echo out any variable.  Special functions are provided to gain access to, for example, "Terminal" and "Session", but do not necessarily require it.  There are no limitations, you may use anything python is capable of.

*Encoding*

  - All other systems are completely agnostic of encoding -- so most systems assume an IBM-PC CP437 encoding, or must specify which "character set" to use. This means a bbs must either conform to english-only, or require connecting clients to chose a specific character set for their terminal emulator, which means compromising to ascii-only art.
  - x/84 primarily supports only UTF-8, with special accommodation for CP437-only terminal encodings, such as SyncTerm.  This allows the same BBS containing CP437-encoded artwork and DOS-emulated Doors (such as Lord) to be presented on modern terminals, yet host any number of UTF-8 supported languages such as japanese, swedish, russian, etc.

.. _synchronet: http://www.synchro.net/
.. _daydream: https://github.com/ryanfantus
.. _enthral: https://github.com/M-griffin/EnthralBBS
.. _mystic: http://mysticbbs.com/
.. _List_of_BBS_software: https://en.wikipedia.org/wiki/List_of_BBS_software


History
=======

`Jeff Quast`_, the author of x/84, first ran his own systems as a young teenager on an IBM-PC compatible, then later began writing his own for the internet telnet protocol in Perl and C on Linux systems since the mid-90's.

Around 2002, he ran his third "bbs" using Mystic on Linux which gained popularity due to its association with a pirate channel he managed on efnet, regularly receiving 30-50 daily callers, which exposed numerous bugs and design issues in mystic.  Frustrated by its closed-source nature and the (intermittent) abandonment of the author, Jeff set out to write his own from-scratch.

He met `Johannes Lundberg`_ of Sweden who had already began writing his own system, initially named just "bbs", this was authored in the Python language, which Jeff was unfamiliar with at the time but quickly adapted to.  Many of the things made difficult in the C language were easily solvable, and the dynamic nature of the language made for very rapid development.  Overnight, a 5,000-line patch was returned to Johannes and they agreed to collaborate on a new system, with focus on the new Unix developer traditions and open source.

They grew apart over time with their forks, Johannes providing a new redesign called "The Progressive (PRSV)", which Jeff re-based and began to contribute to when they re-combined efforts years later.  Johannes continually asserted that he would maintain and later release PRSV, but as his involvement wanned, Jeff renamed his fork as x/84, with the intent to merge upstream some day.

x/84 retains only some of the design and basic variables, such as the concept of a session, userbase, and the echo function, but is otherwise completely rewritten by the work of Jeff alone.  x/84 is a re-imagination of the possibilities of authoring a nostalgic text-mode system analogous to those early dial-up systems.  Targeted for, but not limited to, running a bulletin board over the TCP/IP protocol.

.. _Jeff Quast: https://jeffquast.com/
.. _Johannes Lundberg: http://github.com/johannesl/

Future Directions
=================

basic v3.0 roadmap:

* python3 using async i/o
* windows support, requires ansi.sys support emulation for PDCurses in blessed
* ftp, ftps, fxp support
* modeling (using 'schematics' project) for userbase, messagebase, etc. 
* support for agoranet, zeronet, etc. messaging networks

Feel free to contribute ideas as a github issue.
