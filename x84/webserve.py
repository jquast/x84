"""
x84 web server
"""

import web

def start(web_modules):
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
