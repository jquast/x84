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

QUEUES = None
LOCKS = None

def start(web_modules):
    """ fire up a web server with the given modules as endpoints """
    from threading import Thread
    import logging

    global QUEUES, LOCKS
    logger = logging.getLogger()
    QUEUES = dict()
    LOCKS = dict()
    urls = list()
    funcs = globals()

    for mod in web_modules:
        exec 'from x84.webmodules import %s' % mod
        exec 'api = %s.web_module()' % mod
        urls += api['urls']

        for key in api['funcs']:
            funcs[key] = api['funcs'][key]

    t = Thread(target=server_thread, args=(urls, funcs,))
    t.daemon = True
    t.start()
    logger.info(u'Web modules: %s' % u', '.join(web_modules))

def server_thread(urls, funcs):
    """ thread for running the web server """
    from x84.bbs import ini
    from web.wsgiserver import CherryPyWSGIServer

    CherryPyWSGIServer.ssl_certificate = ini.CFG.get('web', 'cert')
    CherryPyWSGIServer.ssl_private_key = ini.CFG.get('web', 'key')

    if ini.CFG.has_option('web', 'chain'):
        CherryPyWSGIServer.ssl_certificate_chain = ini.CFG.get('web', 'chain')

    app = web.application(urls, funcs)
    web.httpserver.runsimple(app.wsgifunc(), (ini.CFG.get('web', 'addr'), ini.CFG.getint('web', 'port')))
