import datetime
import email.utils
import logging
import os
import socket
import SocketServer
import string
from threading import Lock, Thread
import time

import sqlitedict

from x84.bbs import ini
from x84.bbs.dbproxy import DBProxy
from x84.bbs.msgbase import MSGDB, TAGDB
from x84.bbs.session import Session
from x84.terminal import Terminal


log = logging.getLogger()


class Error(object):
    AUTH_NO_PERMISSION = '502 No permission'
    CMDSYNTAXERROR     = '501 Command syntax error (or un-implemented option)'
    NOARTICLERETURNED  = '420 No article(s) selected'
    NOARTICLESELECTED  = '420 No current article has been selected'
    NODESCAVAILABLE    = '481 Groups and descriptions unavailable'
    NOGROUPSELECTED    = '412 No newsgroup has been selected'
    NOIHAVEHERE        = '435 Article not wanted - do not send it'
    NONEXTARTICLE      = '421 No next article in this group'
    NOPREVIOUSARTICLE  = '422 No previous article in this group'
    NOSTREAM           = '500 Command not understood'
    NOSUCHARTICLE      = '430 No such article'
    NOSUCHARTICLENUM   = '423 No such article in this group'
    NOSUCHGROUP        = '411 No such news group'
    NOTCAPABLE         = '500 Command not recognized'
    NOTPERFORMED       = '503 Program error, function not performed'
    POSTINGFAILED      = '441 Posting failed'
    TIMEOUT            = '503 Timeout after %s seconds, closing connection.'


class Status(object):
    ARTICLE         = '220 %s %s All of the article follows'
    AUTH_ACCEPTED   = '281 Authentication accepted'
    AUTH_CONTINUE   = '381 More authentication information required'
    AUTH_REQUIRED   = '480 Authentication required'
    BODY            = '222 %s %s article retrieved - body follows'
    CLOSING         = '205 Closing connection - goodbye!'
    DATE            = '111 %s'
    EXTENSIONS      = '215 Extensions supported by server.'
    GROUPSELECTED   = '211 %s %s %s %s group selected'
    HEAD            = '221 %s %s article retrieved - head follows'
    HELPMSG         = '100 Help text follows'
    LIST            = '215 List of newsgroups follows'
    LISTGROUP       = '211 %s %s %s %s Article numbers follow (multiline)'
    LISTNEWSGROUPS  = '215 Information follows'
    NEWGROUPS       = '231 List of new newsgroups follows'
    NEWNEWS         = '230 List of new articles by message-id follows'
    NOPOSTMODE      = '201 Hello, you can\'t post'
    OVERVIEWFMT     = '215 Information follows'
    POSTMODE        = '200 Hello, you can post'
    POSTSUCCESSFULL = '240 Article received ok'
    READONLYSERVER  = '440 Posting not allowed'
    READYNOPOST     = '201 %s X/84 server ready (no posting allowed)'
    READYOKPOST     = '200 %s X/84 server ready (posting allowed)'
    SENDARTICLE     = '340 Send article to be posted'
    SERVER_VERSION  = '200 X/84'
    SLAVE           = '202 Slave status noted'
    STAT            = '223 %s %s article retrieved - request text separately'
    XGTITLE         = '282 List of groups and descriptions follows'
    XHDR            = '221 Header follows'
    XOVER           = '224 Overview information follows'
    XPAT            = '221 Header follows'


# the currently supported overview headers
overview_headers = (u'Subject:', u'From:', u'Date:', u'Message-ID:',
                    u'References:', u'Bytes:', u'Lines:', u'Xref:full')


def db(schema, table='unnamed'):
    return sqlitedict.SqliteDict(
        os.path.join(ini.CFG.get('system', 'datapath'), schema + '.sqlite3'),
        table,
    )


def get_group_stats(group):
    tag = get_tag(group)
    msgdb = db(MSGDB)
    ids = []
    for idx in msgdb:
        msg = msgdb[idx]
        if tag in map(string.lower, msg.tags):
            ids.append(long(idx) + 1)

    return len(ids), min(ids), max(ids), group


def get_message(tag, idx):
    msgdb = db(MSGDB)
    if str(idx) not in msgdb or tag not in msgdb[str(idx)].tags:
        return None

    msg = msgdb[str(idx)]
    headers = []
    headers.append(u'From: <%s@%s>' % (msg.author, ini.CFG.get('nntp', 'name')))
    recipients = []
    for tag in msg.tags:
        recipients.append(u'<%s@msg.%s>' % (tag, ini.CFG.get('nntp', 'name')))
    headers.append(u'To: %s' % ', '.join(recipients))
    headers.append(u'Subject: %s' % msg.subject)
    headers.append(u'Date: %s' % email.utils.formatdate(
        time.mktime(msg.ctime.timetuple())
    ))
    headers.append(u'Message-Id: %s' % get_message_id(tag, idx))
    if msg.parent:
        headers.append(u'References: %s' % get_message_id(tag, msg.parent))
    headers.append(u'Content-Type: text/plain; charset=UTF-8; format=flowed')
    headers.append(u'Content-Transfer-Encoding: 8bit')
    return u'\r\n'.join(headers), msg.body


def get_message_id(group, idx):
    tag = get_tag(group)
    return u'<x84.%s@%s>' % (
        long(idx) + 1,
        ini.CFG.get('nntp', 'name')
    )


def get_tag(group):
    if group.startswith('x84.'):
        return group[4:].lower()

    elif '.' not in group:
        return group.lower()

    else:
        return None


def get_ARTICLE(group, idx):
    tag = get_tag(group)
    idx = long(idx) - 1
    return get_message(tag, idx)


def has_GROUP(group):
    if group.startswith('x84.'):
        group = group[4:].lower()
        tagdb = db(TAGDB)
        return group in map(string.lower, tagdb)
    else:
        return False

def get_GROUP(group):
    if group.startswith('x84.'):
        group = group[4:].lower()
        msgdb = db(MSGDB)
        total_articles, first_art_num, last_art_num = 0, 99999999999999, 0
        for idx in msgdb:
            msg = msgdb[idx]
            if group not in map(string.lower, msg.tags):
                continue

            total_articles += 1
            first_art_num = min(first_art_num, long(idx) + 1)
            last_art_num = max(last_art_num, long(idx) + 1)

        return total_articles, first_art_num, last_art_num
    else:
        return False


def get_LIST():
    tagdb = db(TAGDB)
    msgdb = db(MSGDB)
    groups = {}
    for idx in msgdb:
        msg = msgdb[idx]
        idx = long(idx)
        for tag in msg.tags:
            if tag not in groups:
                groups[tag] = [idx + 1, idx + 1]
            else:
                groups[tag] = [
                    min(groups[tag][0], idx + 1),
                    max(groups[tag][1], idx + 1),
                ]

    output = []
    for group in sorted(groups):
        first, last = groups[group]
        output.append('x84.%s %d %d n' % (group, first, last))

    return '\r\n'.join(output)


def get_LIST_NEWSGROUPS():
    tagdb = db(TAGDB)
    groups = []
    for group in sorted(tagdb):
        groups.append('x84.%s %s' % (group, group))

    return '\r\n'.join(groups)


def get_LISTGROUP(group):
    tag = get_tag(group)
    msgdb = db(MSGDB)
    ids = []
    for idx in msgdb:
        if tag in map(string.lower, msgdb[idx].tags):
            ids.append(str(long(idx) + 1))

    ids.sort(lambda a, b: cmp(long(a), long(b)))
    return '\r\n'.join(ids)


def get_NEWGROUPS(ts, group='%'):
    return None


def get_XGTITLE(pattern=None):
    tagdb = db(TAGDB)
    groups = []
    for group in sorted(tagdb):
        if pattern is not None and pattern not in group:
            continue
        groups.append('x84.%s %s' % (group, group))

    if groups:
        return '\r\n'.join(groups)
    else:
        return None


def get_XHDR(group, header, style, ranges):
    tag = get_tag(group)
    if tag is None:
        return ''

    header = header.upper()

    if style == 'range':
        if len(ranges) == 2:
            range_end = int(ranges[1]) - 1
        else:
            range_end = get_group_count(group)

        ids = range(int(ranges[0]) - 1, range_end + 1)
    else:
        ids = (int(ranges[0]) - 1,)

    headers = []
    for idx in ids:
        if header == 'MESSAGE-ID':
            headers.append(get_message_id(group, idx))
            continue

        if header == 'XREF':
            headers.append(u'%d %s %s:%d' % (
                idx + 1,
                ini.CFG.get('nntp', 'name'),
                group,
                idx + 1,
            ))
            continue

        msg = get_message(tag, idx)
        print msg
        if header == 'BYTES':
            headers.append(u'%d %d' % (idx + 1, len(msg[1])))

        elif header == 'LINES':
            headers.append(u'%d %d' % (idx + 1, len(msg[1].splitlines())))

        else:
            items = [line.split(': ') for line in msg[0].splitlines()]
            h = dict((k.lower(), v) for k, v in items)
            if header.lower() in h:
                headers.append(u'%d %s' % (idx + 1, h[header.lower()]))

    return u'\r\n'.join(headers)


def get_XOVER(group, start_idx, end_idx='ggg'):
    msgdb = db(MSGDB)

    start_idx = long(start_idx) - 1
    if end_idx == 'ggg':
        end_idx = get_group_count(group)
    else:
        end_idx = long(end_idx) - 1

    overviews = []
    if has_GROUP(group):
        tag = get_tag(group)
        for idx in xrange(start_idx, end_idx + 1):
            msg = msgdb[str(idx)]
            if not tag in map(string.lower, msg.tags):
                continue

            xref = u'Xref: %s x84.%s %s' % (
                ini.CFG.get('nntp', 'name'),
                tag,
                long(idx) + 1,
            )

            if msg.parent:
                reference = u'x84.%d@%s' % (
                    msg.parent + 1,
                    ini.CFG.get('nntp', 'name'),
                )
            else:
                reference = ''

            # message_number <tab> subject <tab> author <tab> date <tab>
            # message_id <tab> reference <tab> bytes <tab> lines
            # <tab> xref
            overviews.append(u'\t'.join((
                str(long(idx) + 1),
                msg.subject.replace('\t', '    '),
                msg.author,
                '0',
                get_message_id(tag, idx),
                reference,
                str(len(msg.body.encode('utf-8'))),
                str(len(msg.body.splitlines())),
                xref,
            )))

    return '\r\n'.join(overviews)


if os.name == 'posix':
    class NNTPServer(SocketServer.ForkingTCPServer):
        allow_reuse_address = 1

else:
    class NNTPServer(SocketServer.ThreadingTCPServer):
        allow_reuse_address = 1


class NNTPHandler(SocketServer.StreamRequestHandler):
    commands = (
        'ARTICLE', 'AUTHINFO', 'BODY', 'DATE', 'GROUP', 'HDR', 'HEAD',
        'HELP', 'IHAVE', 'LAST', 'LIST', 'LISTGROUP', 'MODE', 'NEWNEWS',
        'NEWGROUPS', 'NEXT', 'OVER', 'POST', 'QUIT', 'SLAVE', 'STAT',
        'XGTITLE', 'XHDR', 'XOVER', 'XPAT', 'XROVER', 'XVERSION',
    )
    terminated = False
    selected_article = 'ggg'
    selected_group = 'ggg'
    sending_article = 0
    article_lines = []
    broken_oe_checker = 0

    def __init__(self, *args, **kwargs):
        SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)

    def get_timestamp(self, date, times, gmt=True):
        # like the new NNTP draft explains...
        if len(date) == 8:
            year = date[:4]
        else:
            local_year = str(time.localtime()[0])
            if date[:2] > local_year[2:4]:
                year = "19%s" % (date[:2])
            else:
                year = "20%s" % (date[:2])
        ts = time.mktime((int(year), int(date[2:4]), int(date[4:6]), int(times[:2]), int(times[2:4]), int(times[4:6]), 0, 0, 0))
        if gmt:
            return time.gmtime(ts)
        else:
            return time.localtime(ts)

    def handle(self):
        self.send_response(Status.READYNOPOST % ini.CFG.get('nntp', 'name'))

        while not self.terminated:
            if self.sending_article == 0:
                self.article_lines = []

            try:
                self.inputline = self.rfile.readline()
            except IOError:
                continue

            if not self.sending_article:
                line = self.inputline.strip()
                log.info('<<< %s' % line)
            else:
                line = self.inputline

            if (not self.sending_article) and (line == ''):
                self.broken_oe_checker += 1
                if self.broken_oe_checker == 10:
                    self.terminated = True
                continue

            self.tokens = line.split(' ')
            command = self.tokens[0].upper()
            if command == 'POST':
                self.send_response(Status.READONLYSERVER)

            elif self.sending_article:
                if self.inputline == '.\r\n':
                    self.sending_article = 0
                    try:
                        self.do_POST()
                    except:
                        raise
                        self.send_response(Error.POSTINGFAILED)
                    continue

            else:
                if command in self.commands:
                    try:
                        getattr(self, 'do_%s' % command)()
                    except AttributeError:
                        raise
                        self.send_response(Error.CMDSYNTAXERROR)

                else:
                    self.send_response(Error.NOTCAPABLE)

    def send_response(self, message):
        log.info('>>> %s' % message)
        #self.wfile.write(message + '\r\n')
        #self.wfile.write(message + u'\r\n')
        #self.wfile.flush()
        line = message + u'\r\n'
        while line:
            sent = self.connection.send(line.encode('utf-8'))
            line = line[sent:]

    # commands

    def do_ARTICLE(self):
        '''
        ARTICLE nnn|<message-id>
        '''
        if len(self.tokens) != 2:
            return self.send_response(Error.CMDSYNTAXERROR)

        if self.selected_group == 'ggg':
            return self.send_response(Error.NOGROUPSELECTED)

        if self.tokens[1].find('<') != -1:
            self.tokens[1] = self.get_number_from_msg_id(self.tokens[1])
            report_article_number = 0
        else:
            report_article_number = long(self.tokens[1])

        result = get_ARTICLE(self.selected_group, self.tokens[1])
        if result == None:
            self.send_response(Error.NOSUCHARTICLENUM)

        else:
            # Only set the internally selected article if the article number
            # variation is used
            if len(self.tokens) == 2 and self.tokens[1].find('<') == -1:
                self.selected_article = self.tokens[1]

            response = Status.ARTICLE % (
                report_article_number,
                get_message_id(self.selected_group, self.selected_article),
            )
            self.send_response("%s\r\n%s\r\n\r\n%s\r\n." % (
                response,
                result[0],
                result[1],
            ))

    def do_DATE(self):
        now = datetime.datetime.now()
        self.send_response(Status.DATE % (now.strftime('%Y%m%d%H%M%S')))

    def do_GROUP(self):
        if len(self.tokens) != 2:
            return self.send_response(Error.CMDSYNTAXERROR)

        if not has_GROUP(self.tokens[1]):
            return self.send_response(Error.NOSUCHGROUP)

        self.selected_group = self.tokens[1]
        total_articles, first_art_num, last_art_num = get_GROUP(self.tokens[1])
        self.send_response(Status.GROUPSELECTED % (
            total_articles,
            first_art_num,
            last_art_num,
            self.tokens[1],
        ))

    def do_LIST(self):
        if len(self.tokens) == 2 and self.tokens[1].upper() == 'OVERVIEW.FMT':
            return self.send_response("%s\r\n%s\r\n." % (
                Status.OVERVIEWFMT,
                "\r\n".join(overview_headers)
            ))

        elif len(self.tokens) == 2 and self.tokens[1].upper() == 'EXTENSIONS':
            return self.send_response("%s\r\n%s\r\n." % (
                Status.EXTENSIONS,
                "\r\n".join(self.extensions)
            ))

        elif len(self.tokens) > 1 and self.tokens[1].upper() == 'NEWSGROUPS':
            return self.do_LIST_NEWSGROUPS()

        elif len(self.tokens) == 2:
            return self.send_response(Error.NOTPERFORMED)

        result = get_LIST()
        self.send_response("%s\r\n%s\r\n." % (Status.LIST, result))

    def do_LIST_NEWSGROUPS(self):
        if len(self.tokens) > 3:
            return self.send_response(Error.CMDSYNTAXERROR)

        if len(self.tokens) == 3:
            info = get_XGTITLE(self.tokens[2])

        else:
            info = get_XGTITLE()

        self.send_response("%s\r\n%s\r\n." % (Status.LISTNEWSGROUPS, info))

    def do_LISTGROUP(self):
        '''
        LISTGROUP [ggg]
        '''
        if len(self.tokens) > 2:
            return self.send_response(Error.CMDSYNTAXERROR)

        if len(self.tokens) == 2:
            if not has_GROUP(self.tokens[1]):
                return self.send_response(Error.NOSUCHGROUP)
            numbers = get_LISTGROUP(self.tokens[1])

        else:
            if self.selected_group == 'ggg':
                return self.send_response(Error.NOGROUPSELECTED)
            numbers = get_LISTGROUP(self.selected_group)

        check = numbers.split('\r\n')
        if len(check) > 0:
            self.selected_article = check[0]
            if len(self.tokens) == 2:
                self.selected_group = self.tokens[1]
        else:
            self.selected_article = 'ggg'

        self.send_response("%s\r\n%s\r\n." % (
            Status.LISTGROUP % (get_group_stats(self.selected_group)),
            numbers,
        ))

    def do_MODE(self):
        if self.tokens[1].upper() == 'READER':
            self.send_response(Status.NOPOSTMODE)

        elif self.tokens[1].upper() == 'STREAM':
            self.send_response(Error.NOSTREAM)

    def do_NEWGROUPS(self):
        '''
        NEWGROUPS date time [GMT] [<distributions>]
        '''
        if len(self.tokens) < 3 or len(self.tokens) > 5:
            return self.send_response(Error.CMDSYNTAXERROR)

        if len(self.tokens) > 3 and self.tokens[3] == 'GMT':
            ts = self.get_timestamp(self.tokens[1], self.tokens[2], True)
        else:
            ts = self.get_timestamp(self.tokens[1], self.tokens[2], False)

        groups = get_NEWGROUPS(ts)
        if groups == None:
            self.send_response(Status.NEWGROUPS + '\r\n.')
        else:
            self.send_response(Status.NEWGROUPS + '\r\n' + groups + '\r\n.')

    def do_OVER(self):
        return self.do_XOVER()

    def do_QUIT(self):
        self.terminated = True
        self.send_response(Status.CLOSING)

    def do_SLAVE(self):
        self.send_response(Status.SLAVE)

    def do_XHDR(self):
        if (len(self.tokens) < 2) or (len(self.tokens) > 3):
            return self.send_response(Error.CMDSYNTAXERROR)

        if self.selected_group == 'ggg':
            return self.send_response(Error.NOGROUPSELECTED)

        #if (self.tokens[1].upper() != 'SUBJECT') and (self.tokens[1].upper() != 'FROM'):
        #    return self.send_response(Error.CMDSYNTAXERROR)

        if len(self.tokens) == 2:
            if self.selected_article == 'ggg':
                return self.send_response(Error.NOARTICLESELECTED)

            info = get_XHDR(
                self.selected_group,
                self.tokens[1],
                'unique',
                (self.selected_article,)
            )

        else:
            # check the XHDR style
            if self.tokens[2].find('@') != -1:
                self.tokens[2] = self.get_number_from_msg_id(self.tokens[2])
                info = get_XHDR(
                    self.selected_group,
                    self.tokens[1],
                    'unique',
                    (self.tokens[2],)
                )

            else:
                ranges = self.tokens[2].split('-')
                if ranges[1] == '':
                    info = get_XHDR(
                        self.selected_group,
                        self.tokens[1],
                        'range',
                        (ranges[0],),
                    )
                else:
                    info = get_XHDR(
                        self.selected_group,
                        self.tokens[1],
                        'range',
                        (ranges[0], ranges[1]),
                    )

        if info is None:
            self.send_response(Error.NOTCAPABLE)

        else:
            self.send_response("%s\r\n%s\r\n." % (Status.XHDR, info))

    def do_XOVER(self):
        if self.selected_group == 'ggg':
            return self.send_response(Error.NOGROUPSELECTED)

        if len(self.tokens) == 1:
            if self.selected_article == 'ggg':
                return self.send_response(Error.NOARTICLESELECTED)
            else:
                overviews = get_XOVER(
                    self.selected_group,
                    self.selected_article,
                    self.selected_article,
                )

        else:
            if self.tokens[1].find('-') == -1:
                overviews = get_XOVER(
                    self.selected_group,
                    self.tokens[1],
                    self.tokens[1],
                )
            else:
                ranges = self.tokens[1].split('-')
                if ranges[1] == '':
                    overviews = get_XOVER(
                        self.selected_group,
                        ranges[0],
                    )
                else:
                    overviews = get_XOVER(
                        self.selected_group,
                        ranges[0],
                        ranges[1],
                    )

        if overviews is None:
            return self.send_response(Error.NOTCAPABLE)

        if len(overviews) == 0:
            return self.send_response(Status.XOVER + '\r\n.')

        else:
            return self.send_response(Status.XOVER + '\r\n' + overviews + '\r\n.')


def start():
    import logging
    logger = logging.getLogger()

    t = Thread(target=server_thread)
    t.daemon = True
    t.start()
    logger.info(u'NNTP Server starting')


def server_thread():
    from x84.bbs import ini

    addr = ini.CFG.get('nntp', 'addr')
    port = ini.CFG.getint('nntp', 'port')
    server = NNTPServer((addr, port), NNTPHandler)
    server.serve_forever()
