========================
Running a message server
========================

Through the web modules system, x/84 provides a clever ability
of intra-bbs messaging through a json-formatted RESTful API.

This is an experimental feature recently added to v2.0, herein
describes the process for beginning a message server, "hub", and
a polling and publishing message client, "leaf".  Both the hub
and leaf nodes are x/84 systems: the hub, running a https server
and the client polling for messages and publishing through the
REST api of the hub.

Configuring a hub
=================

Firstly, an SSL certificate and matching dnsname of the hub
is *required*. The following sections assume files, given the
domain ``1984.ws``, and were created by using sslmate_::

    -rw-r--r-- 1 root root 5982 Jan 01 00:00 /etc/ssl/www.1984.ws.chained.crt
    -rw-r--r-- 1 root root 1879 Jan 01 00:00 /etc/ssl/www.1984.ws.crt
    -rw------- 1 root root 1679 Jan 01 00:00 /etc/ssl/www.1984.ws.key

Then, the ``default.ini`` file is modified to be extended with the
following details::

    [web]
    enabled = yes
    addr = 88.80.6.213
    port = 8443
    key = /etc/ssl/www.1984.ws.key
    cert = /etc/ssl/www.1984.ws.crt
    chain = /etc/ssl/www.1984.ws.chained.crt
    modules = msgserve

    [msg]
    server_tags = defnet

The ``addr`` and ``port`` of section ``[web]`` keys define the TCP/IP address
and port binded by the web server, and ``modules`` defines a list of scripts
from folder ``x84/webmodules`` served -- here, we define ``msgserve``.
As our serving host has multiple external IP addresses, we choose only the IP
address matching our dnsname **1984.ws**.  The ``key``, ``chain``, and ``cert``
are references to the SSL certificate files retrieved when running the sslmate_
purchase utility.

Messaging on x/84 implements the concept of "tags" -- the most common of them
are tags ``public`` and ``private`` -- though any arbitrary tag may be applied.
The ``server_tags`` value of section ``[msg]`` defines a single "tag", that, for
all messages with such tag, are served externally to the leaf nodes that poll
for new messages.  Here, we chose ``defnet`` -- to signify the "default x/84
messaging network".

When restarting x/84, we may see the log info message::

    INFO   webserve.py:223 https listening on 88.80.6.213:8443/tcp

Configuring a leaf node
=======================

On the hub system as a user of the 'sysop' group, enter the 'sysop' menu
from the main menu, and choose 'a'dd new leaf node.

It's output will be the recommended configuration for the leaf node's
``default.ini``. You may need to adjust the ``base_url`` value to reflect
your external dnsname (the local bind address is used, by default)::

        [msgnet_defnet]
        url_base = https://88.80.6.213:8443/
        board_id = 1
        token = 6MvmGtvMfDF9mkuCfyGxU2IBMmFPhP8ZC70oI0hwKBk=
        poll_interval = 300

        [msg]
        network_tags = defnet

Then, provide the sysop of the client bbs this output, and suggest
to augment their ``default.ini`` with its contents and restart the
leaf node.

Authorship
==========

This extension to x/84 was authored by `@haliphax`_, who
also hosted the first *hub* server on host ``oddnetwork.org``.


.. _sslmate: http://sslmate.com/
.. _@haliphax: http://github.com/haliphax/
