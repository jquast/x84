""" last callers web module for x/84. """

import web
from datetime import datetime
import json
from x84.bbs import DBProxy
from x84.bbs.ini import CFG


class LastCallersApi(object):

    """ Last callers demonstration API endpoint """

    def GET(self, num=10):
        """ Return last x callers """

        num = int(num)
        callers = DBProxy('lastcalls', use_session=False).items()
        last = sorted(callers[-num:], reverse=True,
                      key=lambda caller: caller[1][0])

        # output JSON instead?
        if 'json' in web.input(_method='get'):
            return json.dumps(last)

        callers_html = ''
        board = CFG.get('system', 'bbsname', 'x/84')
        page_title = 'Last {num} Callers to {board}'.format(
            num=num, board=board)

        for caller in last:
            callers_html += ''.join(('<li><b>{who}</b> {affil} ',
                                     '<small>at {when}</small></li>')).format(
                who=caller[0],
                affil='(%s)' % caller[1][2] if caller[1][2] else '',
                when=datetime.fromtimestamp(caller[1][0]))

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
                    {callers_html}
                </ul>
            </body>
            </html>
            """.format(page_title=page_title, callers_html=callers_html)
        return output


def web_module():
    """
    Setup the module and return a dict of its REST API.

    Called only once on server start.
    """

    return {
        'urls': ('/lastcallers/([0-9]+)/?', 'lc', '/lastcallers/?', 'lc'),
        'funcs': {
            'lc': LastCallersApi
        }
    }
