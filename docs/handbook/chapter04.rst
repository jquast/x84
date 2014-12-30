=====================
Chapter 4: the kernel
=====================

x/84 is configured as a separate 'kernel' and 'userland' scripting path to be
optionally located at two different filepaths.

Any changes to engine internals bump release majors. Scripts are encouraged to
require as little modification as possible over time to maintain compatibility
with major releases.

In this chapter we'll go trough some of the core kernel components and what
they stand for.

Engine
======

:API reference: `x84.engine <../api/x84/engine.html>`_

The engine is at the heart of the operation, and makes all the various
components of the kernel talk to the userland components. It's the home of the
main asynchronous event loop, handling new client connections, locks, and I/O
from and to the clients.

Terminal
========

:API reference: `x84.bbs.terminal <../api/x84/bbs/terminal.html>`_

Session
=======

:API reference: `x84.bbs.session <../api/x84/bbs/session.html>`_

The session holds information about the current user, its terminal
capabilities and environment settings.
