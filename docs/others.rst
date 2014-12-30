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
