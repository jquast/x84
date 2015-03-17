==========
Web server
==========

An optional web server is provided in x/84 using the basic `web.py`_ python
library.  It is possible to build web "endpoints" that may make use of x/84's
database and configuration items, these are called "web modules".  Of the default
board, intra-bbs messaging is provided by a web module, for example.

Starting a web server
=====================

Of your ``~/.x84/default.ini`` file, set the configuration of the ``[web]`` section
value ``enabled = yes``  (by default, it is ``no``).  You will also require a
certificate, key, and sometimes a chain certificate file -- **only** HTTPS is
supported at this time.  This is documented in more detail in the "Configuring a
hub" section of the `message network`_ page.

For the server to successfully launch, at least one module must be enabled, the
simple example modules ``oneliners, lastcallers`` may be enabled, for example::

    [web]
    enabled = yes
    addr = 123.123.123.123
    port = 8443
    key = /etc/ssl/www.1984.ws.key
    cert = /etc/ssl/www.1984.ws.crt
    chain = /etc/ssl/www.1984.ws.chained.crt
    modules = oneliners, lastcallers

If everything is configured properly, you should see something like this at
startup::

    Mon-01-01 12:00AM INFO       webserve.py:207 https listening on 123.123.123.123:8443/tcp

Lookup path
===========

There are only two lookup paths for the values defined by ``modules``,
preferably, the sub-folder, ``webmodules/`` of your ``scriptpath`` configuration
of section ``[system]`` in your ``~/.x84/default.ini`` file.  These are imported
by their python module name, so file ``scriptpath/webmodules/oneliners.py`` is
simply ``oneliners``.  If the file is not found there, it will then look for it
in the package path of x84, which can be found using command::

        $ python -c 'import os, x84.webmodules; print(os.path.dirname(x84.webmodules.__file__))'


Serving static files
====================

One of x/84's internal web modules is called ``static``. If you enable this
module, x/84 will serve static file content from the ``www-static`` subdirectory
of your system's top-level ``scriptpath``. The top-level refers to the first
item in this array.  If you wish to set the document root to some other
location, use the ``document_root`` option in the ``[web]`` section of your
configuration file. ::

    [web]
    ; other configuration here
    modules = static
    document_root = /var/www

The static files are served from ``/www-static/``, so if your server is
``https://123.123.123.123:8443``, and the file is ``style.css``, it would
be served as ``https://123.123.123.123:8443/www-static/style.css``.

Writing a web module
====================

While some web modules, such as the `message network`_ module,
operate outside of userland and are leveraged by the engine for low-level
functionality. However, you can write your own modules--and even override the
internal modules--by placing your scripts in the ``webmodules`` subdirectory
of your x/84 system's script directory and adding them to the ``modules``
list in the ``[web]`` section of your configuration file.

As examples, two web modules have been included with the "default board"
installed alongside x/84: :module:`x84.default.oneliners` and
:module:`x84.default.lastcallers`. These are rudimentary examples which both
read information from ``DBProxy`` objects and format them for display on the
web. They serve to demonstrate interacting with the engine layer outside of
a terminal session; accepting command options through the use of GET
parameters; how Python classes ultimately translate into URL handlers; and
exposing URL handlers to the x/84 engine process.

The handler class
-----------------

First and foremost, we need to build a class which will be handling our HTTP
requests. x/84's web server uses `web.py`_ internally, and so we give our class
a method function for each `HTTP verb`_ we want it to respond to. For the
purposes of demonstration, the class below will only be responding to GET
requests. ::

    class EchoHandler(object):

        """ Demonstration URL Handler """

        def GET(self, echo=None):
            """ Echo back to the user. """

            if not echo:
                echo = u"I can't hear you!"

            return echo

This class will echo back whatever the user writes in the URL. If the user
doesn't write anything, it will display, "I can't hear you!"

The REST API
------------

Now, we need to inform the x/84 engine process about the existence of our web
module and what URL pattern(s) it should be invoked for. We do this by putting
a root-level ``web_module`` function in our script that returns a ``dict``
object with this information. ::

    def web_module():
        """ Return a dict of our REST API. """

        return {'urls': ('/echo(.*)?', 'echo'), 'funcs': {'echo': EchoHandler}}

The first ``dict`` entry, ``urls``, is a list where pairs of URL patterns and
keywords are associated with one another. The pattern is that each
even-numbered entry (0, 2, 4, 6, ...) is a URL pattern and each following
odd-numbered entry (1, 3, 5, 7, ...) is a keyword for which URL handler should
be invoked for this URL pattern.

The next ``dict`` entry, ``funcs``, is a ``dict`` that translates those
keywords into the class of the web module. In our example, we are translating
the keyword, ``echo``, into the class, ``EchoHandler``.

Enabling the module
-------------------

Now that we've finished with the code, we need to add our new module to the
``modules`` option in the ``[web]`` section of our configuration file. If
we saved our script as ``echo.py`` in the ``webmodules`` subdirectory of our
x/84 system's script path, we would use the name ``echo`` to refer to it
in the configuration file: ::

    [web]
    ; other configuration here
    modules = echo

Next, we will have to restart x/84 in order for the module to be loaded.

Testing the module
------------------

Now, if we visit ``https://123.123.123.123:8443/echo/test`` in our web browser,
we will see: ::

    test

And if we visit ``https://123.123.123.123:8443/echo`` in our web browser, we
will see: ::

    I can't hear you!

Take it further
---------------

This is a very simple example. For a bit more advanced functionality, look at
the source of the :module:`x84.default.webmodules.oneliners` and
:module:`x84.default.webmodules.lastcallers` modules. To take it a step
further still, consider looking at the :module:`x84.webmodules.msgserve`
module in the x/84 server code.

.. _web.py: http://webpy.org/
.. _message network: ./msgnet.rst
.. _HTTP verb: https://wikipedia.org/wiki/Hypertext_Transfer_Protocol#Request_methods
