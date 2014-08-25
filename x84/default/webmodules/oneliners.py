"""
oneliners web module for x/84, https://github.com/jquast/x84
"""

import web
import json
from x84.bbs import DBProxy
from x84.bbs.ini import CFG

class OnelinersApi(object):
    """ Oneliners demonstration API endpoint """

    def GET(self, num=10):
        """ Return last x oneliners """

        num = int(num)
        oneliners = DBProxy('oneliner', use_session=False).items()
        oneliners = [(int(k), v) for (k, v) in
            DBProxy('oneliner', use_session=False).items()]
        last = oneliners[-num:]

        # output JSON instead?
        if 'json' in web.input(_method='get'):
            return json.dumps(last)

        board = CFG.get('system', 'bbsname', 'x/84')
        page_title = 'Last {num} Oneliners on {board}'.format(
            num=num, board=board)
        oneliners_html = ''

        for line in last:
            val = line[1]
            oneliners_html += '<li><b>{alias}:</b> {oneliner}</li>'.format(
                alias=val['alias'], oneliner=val['oneliner'])

        web.header('Content-Type', 'text/html; charset=utf-8', unique=True)
        output = """
            <!DOCTYPE html>
            <html lang="en-US">
            <head>
                <meta charset="utf-8" />
                <title>{page_title}</title>
            </head>
            <body>
                <h1>{page_title}</h1>
                <ul>
                    {oneliners_html}
                </ul>
            </body>
            </html>
            """.format(page_title=page_title, oneliners_html=oneliners_html)
        return output


def web_module():
    """
    Setup the module and return a dict of its REST API.

    Called only once on server start.
    """

    return {
        'urls': ('/oneliners/([0-9]+)/?', 'ol', '/oneliners/?', 'ol'),
        'funcs': {
            'ol': OnelinersApi
        }
    }
