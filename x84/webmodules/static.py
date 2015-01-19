""" Static file server web module for x/84 bbs. """

import web
import os
import mimetypes

class StaticApp(object):

    """ Class for serving static files. """

    static_root = ''
    mime_types = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'text/javascript',
    }

    def GET(self, filename):
        """ Respond to GET method request. """
        if not filename:
            return web.redirect('/www-static/')
        file_url = os.path.join(*filter(lambda txt: txt != '..',
                                        filename.split('/')))
        myfile = os.path.join(StaticApp.static_root, file_url)
        if os.path.isfile(myfile):
            # we're serving a file; use the proper mime type
            mime = mimetypes.guess_type(myfile)
            _, ext = os.path.splitext(myfile.lower())
            mime = StaticApp.mime_types.get(ext, mime)
            web.header('Content-Type', mime, unique=True)
            return open(myfile, 'rb').read()
        elif os.path.isdir(myfile):
            # we're serving a directory; try directory/index.html instead
            if not filename.endswith('/'):
                return web.redirect(''.join([filename, '/']))
            return self.GET('/'.join([filename, 'index.html']))
        # path does not exist; return 404
        return web.notfound()


def web_module():
    """ Expose our REST API. Run only once on server startup. """
    from x84.bbs.ini import get_ini

    # determine document root for web server
    static_root = (get_ini('web', 'document_root')
                   or os.path.join(get_ini('system', 'scriptpath'),
                                   'www-static'))
    StaticApp.static_root = static_root

    return {
        'urls': ('/www-static(/.*)?', 'static'),
        'funcs': {
            'static': StaticApp
        }
    }
