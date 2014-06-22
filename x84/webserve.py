"""
web server for x/84, https://github.com/jquast/x84

To configure the web server, add a [web] section to your default.ini.

The following attributes are required:
 - addr: The address to bind to. Must be resolvable.
 - port: The port number to bind to.
 - cert: The SSL certificate.
 - key: The SSL certificate's key.

The following attribute is optional:
 - chain: The SSL chain certificate.

Example:

[web]
addr = 0.0.0.0
port = 8443
cert = /home/bbs/ssl.cer
key = /home/bbs/ssl.key
chain = /home/bbs/ca.cer
"""

import web

def start(web_modules):
    """ fire up a web server with the given modules as endpoints """
    from x84.bbs import ini
    import logging
    from web.wsgiserver import CherryPyWSGIServer
    # @TODO use functions to dynamically import web.py endpoint classes
    from x84.msgserve import messages

    logger = logging.getLogger()
    CherryPyWSGIServer.ssl_certificate = ini.CFG.get('web', 'cert')
    CherryPyWSGIServer.ssl_private_key = ini.CFG.get('web', 'key')

    if ini.CFG.has_option('web', 'chain'):
        CherryPyWSGIServer.ssl_certificate_chain = ini.CFG.get('web', 'chain')

    urls = list()

    if 'msgserve' in web_modules:
        global messages
        urls += ('/messages/([^/]+)/([^/]*)/?', 'messages')

    app = web.application(urls, globals())
    logger.info(u'Web modules: %s' % u', '.join(web_modules))
    web.httpserver.runsimple(app.wsgifunc(), (ini.CFG.get('web', 'addr'), ini.CFG.getint('web', 'port')))
