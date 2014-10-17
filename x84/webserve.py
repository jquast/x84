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
    from threading import Thread
    import logging
    import sys
    import os
    from x84.bbs.ini import CFG

    logger = logging.getLogger()
    sys.path.insert(0, os.path.expanduser(CFG.get('system', 'scriptpath')))
    urls = ('/favicon.ico', 'favicon')
    funcs = globals()
    funcs['favicon'] = Favicon

    for mod in web_modules:
        module = None

        # first check for it in the scripttpath's webmodules dir
        try:
            module = __import__('webmodules.%s' % mod,
                                fromlist=('webmodules',))
        except ImportError:
            pass

        # fallback to the engine's webmodules dir
        if module is None:
            module = __import__('x84.webmodules.%s' % mod,
                                fromlist=('x84.webmodules',))

        api = module.web_module()
        urls += api['urls']

        for key in api['funcs']:
            funcs[key] = api['funcs'][key]

    t = Thread(target=server_thread, args=(urls, funcs,))
    t.daemon = True
    t.start()
    logger.info(u'Web modules: %s' % u', '.join(web_modules))


class Favicon:
    """ Dummy class for preventing /favicon.ico 404 errors """

    def GET(self):
        pass


def server_thread(urls, funcs):
    """ thread for running the web server """
    from x84.bbs import ini
    from web.wsgiserver import CherryPyWSGIServer
    from web.wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter
    from OpenSSL import SSL

    cert, key, chain = None, None, None

    if ini.CFG.has_option('web', 'cert'):
        cert = ini.CFG.get('web', 'cert')
    if ini.CFG.has_option('web', 'key'):
        key = ini.CFG.get('web', 'key')
    if ini.CFG.has_option('web', 'chain'):
        chain = ini.CFG.get('web', 'chain')

    CherryPyWSGIServer.ssl_adapter = pyOpenSSLAdapter(cert, key, chain)
    CherryPyWSGIServer.ssl_adapter.context = SSL.Context(SSL.SSLv23_METHOD)
    CherryPyWSGIServer.ssl_adapter.context.set_options(SSL.OP_NO_SSLv3)
    CherryPyWSGIServer.ssl_adapter.context.use_certificate_file(cert)
    CherryPyWSGIServer.ssl_adapter.context.use_privatekey_file(key)

    if chain:
        CherryPyWSGIServer.ssl_adapter.context.use_certificate_chain_file(chain)

    CherryPyWSGIServer.ssl_adapter.context.set_cipher_list('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:!aNULL:!MD5:!DSS')

    app = web.application(urls, funcs)
    addr = (ini.CFG.get('web', 'addr'), ini.CFG.getint('web', 'port'))
    web.httpserver.runsimple(app.wsgifunc(), addr)
