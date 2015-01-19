#!/usr/bin/env python2.7
""" web server for x/84. """
import threading
import traceback
import logging
import web
import sys
import os


class Favicon(object):

    """ Dummy class for preventing 404 of ``/favicon.ico`` """

    def GET(self):
        """ GET request callback (does nothing). """
        pass


def _get_fp(section_key, optional=False):
    """ Return filepath of [web] option by ``section_key``. """
    from x84.bbs import get_ini
    value = get_ini(section='web', key=section_key) or None
    if value:
        value = os.path.expanduser(value)
    elif optional:
        return None
    assert value is not None and os.path.isfile(value), (
        'Configuration section [web], key `{section_key}`, '
        'must {optional_exist}identify a path to an '
        'SSL {section_key} file. '
        '(value is {value})'.format(
            section_key=section_key,
            optional_exist=not optional and 'exist and ' or '',
            value=value))
    return value


def get_urls_funcs(web_modules):
    """ Get url function mapping for the given web modules. """
    log = logging.getLogger(__name__)

    # list of url's to route to each module api; defaults to route /favicon.ico
    # to a non-op to avoid 404 errors.
    # See: http://webpy.org/docs/0.3/api#web.application
    urls = ('/favicon.ico', 'favicon')
    funcs = globals()
    funcs['favicon'] = Favicon

    log.debug('add url {0} => {1}'.format(
        '/favicon.ico', Favicon.__name__))

    for mod in web_modules:
        module = None

        # first, check in system PATH (includes SCRIPT_PATH)
        try:
            module = __import__('webmodules.{0}'.format(mod),
                                fromlist=('webmodules',))
        except ImportError:
            # failed to import, check in x84's path, raise naturally
            module = __import__('x84.webmodules.{0}'.format(mod),
                                fromlist=('x84.webmodules',))

        api = module.web_module()

        for key in api['funcs']:
            funcs[key] = api['funcs'][key]

        # use zip to transform (1,2,3,4,5,6,7,8) =>
        # [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]
        # then, use slice to 'step 2' =>
        # [(1, 2), (3, 4), (5, 6), (7, 8)]
        for (url, f_key) in zip(api['urls'], api['urls'][1:])[::2]:
            if f_key not in funcs:
                log.error('module {module} provided url {url_tuple} without '
                          'matching function (available: {f_avail})'
                          .format(module=module,
                                  url_tuple=(url, f_key,),
                                  f_avail=funcs.keys()))
            else:
                log.debug('add url {0} => {1}'.format(
                    url, funcs[f_key].__name__))
        urls += api['urls']
    return urls, funcs


def server(urls, funcs):
    """ Main server thread for running the web server """
    from x84.bbs import get_ini
    from web.wsgiserver import CherryPyWSGIServer
    from web.wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter
    from OpenSSL import SSL

    log = logging.getLogger(__name__)

    cert, key, chain = (_get_fp('cert'),
                        _get_fp('key'),
                        _get_fp('chain', optional=True))

    addr = get_ini(section='web',
                   key='addr'
                   ) or '0.0.0.0'

    port = get_ini(section='web',
                   key='port',
                   getter='getint'
                   ) or 8443

    # List of ciphers made available, composed by haliphax without reference,
    # but apparently to prevent POODLE? This stuff is hard -- the best source
    # would probably be to compare by cloudflare's latest sslconfig file:
    #
    #   https://github.com/cloudflare/sslconfig/blob/master/conf
    #
    cipher_list = (get_ini(section='web', key='cipher_list')
                   or ':'.join((
                       'ECDH+AESGCM',
                       'ECDH+AES256',
                       'ECDH+AES128',
                       'ECDH+3DES',
                       'DH+AESGCM',
                       'DH+AES256',
                       'DH+AES',
                       'DH+3DES',
                       'RSA+AESGCM',
                       'RSA+AES',
                       'RSA+3DES',
                       '!aNULL',
                       '!MD5',
                       '!DSS',
                   )))

    CherryPyWSGIServer.ssl_adapter = pyOpenSSLAdapter(cert, key, chain)
    CherryPyWSGIServer.ssl_adapter.context = SSL.Context(SSL.SSLv23_METHOD)
    CherryPyWSGIServer.ssl_adapter.context.set_options(SSL.OP_NO_SSLv3)

    try:
        CherryPyWSGIServer.ssl_adapter.context.use_certificate_file(cert)
    except Exception:
        # wrap exception to contain filepath to 'cert' file, which will
        # hopefully help the user better understand what otherwise be very
        # obscure.
        error = ''.join(
            traceback.format_exception_only(
                sys.exc_info()[0],
                sys.exc_info()[1])).rstrip()
        raise ValueError('Exception loading ssl certificate file {0!r}: '
                         '{1}'.format(cert, error))

    try:
        CherryPyWSGIServer.ssl_adapter.context.use_privatekey_file(key)
    except Exception:
        # also wrap exception to contain filepath to 'key' file.
        error = ''.join(
            traceback.format_exception_only(
                sys.exc_info()[0],
                sys.exc_info()[1])).rstrip()
        raise ValueError('Exception loading ssl key file {0!r}: '
                         '{1}'.format(key, error))

    if chain is not None:
        (CherryPyWSGIServer.ssl_adapter.context
         .use_certificate_chain_file(chain))

    CherryPyWSGIServer.ssl_adapter.context.set_cipher_list(cipher_list)

    app = web.application(urls, funcs)

    web.config.debug = False

    log.info('https listening on {addr}:{port}/tcp'
             .format(addr=addr, port=port))

    # Runs CherryPy WSGI server hosting WSGI app.wsgifunc().
    web.httpserver.runsimple(app.wsgifunc(), (addr, port))  # blocking


def main(background_daemon=True):
    """
    Entry point to configure and begin web server.

    Called by x84/engine.py, function main() as unmanaged thread.

    :param bool background_daemon: When True (default), this function returns
       and web modules are served in an unmanaged, background (daemon) thread.
       Otherwise, function call to ``main()`` is blocking.
    :rtype: None
    """
    from x84.bbs import get_ini

    log = logging.getLogger(__name__)

    SCRIPT_PATH = get_ini(section='system', key='scriptpath')

    # ensure the SCRIPT_PATH is in os environment PATH for module lookup.
    sys.path.insert(0, os.path.expanduser(SCRIPT_PATH))

    web_modules = get_ini(section='web', key='modules', split=True)

    if not web_modules:
        log.error("web server enabled, but no `modules' "
                  "defined in section [web]")
        return

    log.debug(u'Ready web modules: {0}'.format(web_modules))
    urls, funcs = get_urls_funcs(web_modules)

    if background_daemon:
        t = threading.Thread(target=server, args=(urls, funcs,))
        t.daemon = True
        t.start()
    else:
        server(urls=urls, funcs=funcs)


if __name__ == '__main__':
    # load only the webserver module when executing this script directly.
    #
    # as we are running outside of the 'engine' context, it is necessary
    # for us to initialize the .ini configuration scheme so that the list
    # of web modules and ssl options may be gathered.
    import x84.bbs.ini
    import x84.cmdline
    x84.bbs.ini.init(*x84.cmdline.parse_args())

    # do not execute webserver as a background thread.
    main(background_daemon=False)
