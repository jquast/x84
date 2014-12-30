=======
History
=======

Since early days in digital communications, people have been running various Bulletin Board Systems.  First invented by Ward Christensen for his custom CP/M system on a snowy Chicago day for his local computer club, it is phrased from the analogy that people can dial-in across phone lines using a new computer device, the modem, and post and read messages, just as a traditional community bulletin board.

The x/84 author `Jeff Quast`_ first ran his own systems as a young teenager on an IBM-PC compatible, then later began writing his own for the internet telnet protocol in Perl and C on Linux systems.  Around 2002, he ran his third "bbs" using mystic BBS on Linux which gained popularity due to its association with a pirate channel he managed on efnet, and regularly received 30-50 daily callers, which exposed numerous bugs and design issues in mystic and was frustrated by its closed-source nature and the abandonment by the author, and set out to write his own from-scratch.

He met `Johannes Lundberg` of Sweden who had already began writing his own system, initially named just "bbs", this was authored in the Python language, which Jeff was unfamiliar with at the time but quickly adapted to.  Many of the things made difficult in the C language were easily solvable, and the dynamic nature of the language made for very rapid development.  Overnight, a 5,000-line patch was returned to Johannes and they agreed to collaborate on a new system, with focus on the new Unix developer traditions and open source.

They grew apart over time with their forks, Johannes providing a new redesign called "The Progressive (PRSV)", which Jeff re-based and began to contribute to.  Johannes continually asserted that he would maintain and later release PRSV, but as his involvement wanned, Jeff renamed his fork as x/84. x/84 retains only some of the design and basic variables, such as the concept of a session, userbase, and the echo function, but is otherwise mostly the work of Jeff alone.

x/84 is a re-imagination of the possibilities of authoring a nostalgic text-mode system analogous to those early dial-up systems.  Targeted for, but not limited to, running a bulletin board over the TCP/IP protocol.

.. _Jeff Quast: https://jeffquast.com/
.. _Johannes Lundberg: http://github.com/johannesl/
