'''
NNTP gateway for BBS messages.

Add the following settings to default.ini to enable::

    [nntp]
    addr = 0.0.0.0
    port = 119
    name = hostname.of.nntp.server
    ; Set to "no" to have a read-only server
    post = yes

    ; If you want SSL, include:
    ssl = yes
    ssl_addr = 0.0.0.0
    ssl_port = 563
    cert = /home/bbs/ssl.cer
    key = /home/bbs/ssl.key

'''

import datetime
import email.parser
import email.utils
import io
import logging
import multiprocessing.dummy
import os
import socket
import SocketServer
import string
from threading import Lock, Thread
import time
try:
    import ssl
except ImportError:
    ssl = None

import sqlitedict

from x84.bbs import ini, session
from x84.bbs.dbproxy import DBProxy
from x84.bbs.msgbase import MSGDB, TAGDB
from x84.bbs.userbase import USERDB
from x84.terminal import Terminal


log = logging.getLogger()


class Error(object):
    NOSUCHGROUP        = '411 No such news group'
    NOGROUPSELECTED    = '412 No newsgroup has been selected'
    NOARTICLERETURNED  = '420 No article(s) selected'
    NOARTICLESELECTED  = '420 No current article has been selected'
    NONEXTARTICLE      = '421 No next article in this group'
    NOPREVIOUSARTICLE  = '422 No previous article in this group'
    NOSUCHARTICLENUM   = '423 No such article in this group'
    NOSUCHARTICLE      = '430 No such article'
    NOIHAVEHERE        = '435 Article not wanted - do not send it'
    POSTINGFAILED      = '441 Posting failed'
    NODESCAVAILABLE    = '481 Groups and descriptions unavailable'
    NOENCRYPTION       = '483 Encryption or stronger authentication required'
    NOSTREAM           = '500 Command not understood'
    NOTCAPABLE         = '500 Command not recognized'
    CMDSYNTAXERROR     = '501 Command syntax error (or un-implemented option)'
    AUTH_NO_PERMISSION = '502 No permission'
    NOTAVAILABLE       = '502 Command not available'
    STARTTLSNOTALLOWED = '502 STARTTLS not allowed with active TLS layer'
    NOTPERFORMED       = '503 Program error, function not performed'
    TIMEOUT            = '503 Timeout after %s seconds, closing connection.'
    CANTINITTLS        = '580 Can not initiate TLS negotiation'


class Status(object):
    HELPMSG         = '100 Help text follows'
    CAPABILITYLIST  = '101 Capability list:'
    DATE            = '111 %s'
    POSTMODE        = '200 Hello, you can post'
    READYOKPOST     = '200 %s X/84 server ready (posting allowed)'
    SERVER_VERSION  = '200 X/84'
    NOPOSTMODE      = '201 Hello, you can\'t post'
    READYNOPOST     = '201 %s X/84 server ready (no posting allowed)'
    SLAVE           = '202 Slave status noted'
    CLOSING         = '205 Closing connection - goodbye!'
    GROUPSELECTED   = '211 %s %s %s %s group selected'
    LISTGROUP       = '211 %s %s %s %s Article numbers follow (multiline)'
    EXTENSIONS      = '215 Extensions supported by server.'
    LIST            = '215 List of newsgroups follows'
    LISTNEWSGROUPS  = '215 Information follows'
    OVERVIEWFMT     = '215 Information follows'
    ARTICLE         = '220 %s %s All of the article follows'
    HEAD            = '221 %s %s article retrieved - head follows'
    XHDR            = '221 Header follows'
    XPAT            = '221 Header follows'
    BODY            = '222 %s %s article retrieved - body follows'
    STAT            = '223 %s %s article retrieved - request text separately'
    XOVER           = '224 Overview information follows'
    NEWNEWS         = '230 List of new articles by message-id follows'
    NEWGROUPS       = '231 List of new newsgroups follows'
    POSTSUCCESSFULL = '240 Article received ok'
    AUTH_ACCEPTED   = '281 Authentication accepted'
    XGTITLE         = '282 List of groups and descriptions follows'
    CONTINUEWITHTLS = '382 Continue with TLS negotiation'
    SENDARTICLE     = '340 Send article to be posted'
    AUTH_CONTINUE   = '381 More authentication information required'
    READONLYSERVER  = '440 Posting not allowed'
    AUTH_REQUIRED   = '480 Authentication required'


# supported capabilities
CAPABILITIES = (
    u'VERSION 2',
    u'READER',
)


# the currently supported overview headers
OVERVIEW_HEADERS = (
    u'Subject:',
    u'From:',
    u'Date:',
    u'Message-ID:',
    u'References:',
    u'Bytes:',
    u'Lines:',
    u'Xref:full',
)


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


def get_LIST(post):
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
        output.append('x84.%s %d %d %s' % (
            group,
            first,
            last,
            ['n', 'y'][int(post)]
        ))

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


class NNTPServer(SocketServer.ForkingTCPServer):
    allow_reuse_address = 1


class ForkingSSLServer(SocketServer.ForkingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass,
                 bind_and_activate=True, ssl_cert=None, ssl_key=None):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key

    def get_request(self):
        client, address = self.socket.accept()
        return ssl.wrap_socket(
                client,
                server_side=True,
                certfile=self.ssl_cert,
                keyfile=self.ssl_key,
            ), address


class NNTPSServer(ForkingSSLServer):
    allow_reuse_address = 1


class NNTPHandler(SocketServer.StreamRequestHandler):
    commands = (
            'ARTICLE',
            'AUTHINFO',
            'BODY',
            'CAPABILITIES',
            'DATE',
            'GROUP',
            'HDR',
            'HEAD',
            'HELP',
            'IHAVE',
            'LAST',
            'LIST',
            'LISTGROUP',
            'MODE',
            'NEWNEWS',
            'NEWGROUPS',
            'NEXT',
            'OVER',
            'POST',
            'QUIT',
            'SLAVE',
            'STARTTLS',
            'STAT',
            'XGTITLE',
            'XHDR',
            'XOVER',
            'XPAT',
            'XROVER',
            'XVERSION',
    )
    auth              = False
    auth_username     = None
    terminated        = False
    selected_article  = 'ggg'
    selected_group    = 'ggg'
    sending_article   = False
    article_lines     = []
    broken_oe_checker = 0

    def __init__(self, *args, **kwargs):
        SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)

    def setup(self):
        SocketServer.StreamRequestHandler.setup(self)
        self.peer = self.connection.getpeername()
        log.info('Accepted new NNTP connection from %s:%d' % self.peer)
        log.info('PID=%d' % os.getpid())

        # Setup dummy Terminal and Session
        inp_recv, inp_send = multiprocessing.Pipe(duplex=False)
        out_recv, out_send = multiprocessing.Pipe(duplex=False)
        lock = multiprocessing.Lock()

        term = Terminal('dumb', io.BytesIO(), 25, 80)
        session.SESSION = session.Session(
            term,
            inp_recv,
            out_send,
            '%s:%d' % self.peer,
            {},
            lock,
        )

    def finish(self):
        self.peer = self.connection.getpeername()
        SocketServer.StreamRequestHandler.finish(self)
        log.info('Lost NNTP connection with %s:%d' % self.peer)
        log.info('PID=%d' % os.getpid())

    def authenticate(self, username, password):
        from x84.bbs import get_user

        if not username or not password:
            return False

        userdb = db(USERDB)
        user = userdb[username]
        if user.auth(password.decode('utf-8')):
            self.auth = True
        else:
            self.auth = False

        return self.auth

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
        ts = time.mktime((
            int(year),
            int(date[2:4]),
            int(date[4:6]),
            int(times[:2]),
            int(times[2:4]),
            int(times[4:6]),
            0, 0, 0
        ))
        if gmt:
            return time.gmtime(ts)
        else:
            return time.localtime(ts)

    @property
    def readonly(self):
        post = False
        try:
            post = ini.CFG.getboolean('nntp', 'post')
        except:
            pass

        return not post

    def handle(self):
        name = ini.CFG.get('nntp', 'name')

        if not self.readonly:
            self.send_response(Status.READYOKPOST % name)
        else:
            self.send_response(Status.READYNOPOST % name)

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
                log.info('<p<\n%s' % line.rstrip())

            if (not self.sending_article) and (line == ''):
                self.broken_oe_checker += 1
                if self.broken_oe_checker == 10:
                    self.terminated = True
                continue

            self.tokens = line.split(' ')
            command = self.tokens[0].upper()
            if command == 'POST':
                if self.readonly:
                    self.send_response(Status.READONLYSERVER)
                else:
                    if not self.auth:
                        self.send_response(Status.AUTH_REQUIRED)
                    else:
                        self.sending_article = True
                        self.send_response(Status.SENDARTICLE)

            elif self.sending_article:
                if self.inputline == '.\r\n':
                    self.sending_article = False
                    try:
                        self.do_POST()
                    except:
                        raise
                        self.send_response(Error.POSTINGFAILED)
                    continue
                self.article_lines.append(line)

            else:
                if command not in ('AUTHINFO', 'MODE') and not self.auth:
                    self.send_response(Status.AUTH_REQUIRED)

                elif command in self.commands:
                    try:
                        getattr(self, 'do_%s' % command)()
                    except AttributeError:
                        raise
                        self.send_response(Error.CMDSYNTAXERROR)

                else:
                    self.send_response(Error.NOTCAPABLE)

    def send_response(self, message):
        log.info('>>> %s' % message)
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

    def do_AUTHINFO(self):
        '''
        AUTHINFO USER userame
        AUTHINFO PASS password
        AUTHINFO SIMPLE username password
        '''
        if len(self.tokens) != 3:
            return self.send_response(Error.CMDSYNTAXERROR)

        if self.readonly:  # Whatever :-)
            return self.send_response(Status.AUTH_ACCEPTED)

        if self.tokens[1].upper() == 'USER':
            self.auth_username = self.tokens[2]
            self.send_response(Status.AUTH_CONTINUE)

        elif self.tokens[1].upper() == 'PASS':
            if self.authenticate(self.auth_username, self.tokens[2]):
                self.send_response(Status.AUTH_ACCEPTED)
            else:
                self.send_response(Error.AUTH_NO_PERMISSION)
                self.auth_username = None

    def do_CAPABILITIES(self):
        capabilities = CAPABILITIES
        try:
            if ini.CFG.getboolean('nntp', 'ssl'):
                capabilities += (u'STARTTLS',)
        except:
            pass

        if not self.readonly and self.auth:
            capabilities += (u'POST',)

        self.send_response(u'%s\r\n%s\r\n.' % (
            Status.CAPABILITYLIST,
            u'\r\n'.join(capabilities),
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

    def do_HDR(self):
        return self.do_XHDR()

    def do_LIST(self):
        if len(self.tokens) == 2 and self.tokens[1].upper() == 'OVERVIEW.FMT':
            return self.send_response("%s\r\n%s\r\n." % (
                Status.OVERVIEWFMT,
                "\r\n".join(OVERVIEW_HEADERS)
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

        result = get_LIST(not self.readonly)
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

    def do_POST(self):
        from x84.bbs.msgbase import Msg

        lines = ''.join(self.article_lines)
        print repr(lines)
        parser = email.parser.Parser()
        parsed = parser.parsestr(lines)

        for k, v in zip(parsed.keys(), parsed.values()):
            print k, v

        if not parsed.has_key('newsgroups'):
            return self.send_response(Error.POSTINGFAILED + ': specify group')

        if parsed.has_key('content-type'):
            content_type = parsed['content-type'].split(';')[0]
            if content_type != 'text/plain':
                return self.send_response(Error.POSTINGFAILED + ': you are '
                                          'sending %s, but you should send in '
                                          'text/plain' % content_type)

        tagdb = db(TAGDB)
        tag = get_tag(parsed['newsgroups'])
        if tag not in tagdb:
            log.warning('No such tag "%s"' % tag)

        codec = 'ascii'
        codecs = filter(None, parsed.get_charsets())
        if codecs:
            codec = codecs[0]

        body = parsed.get_payload()
        try:
            body = body.decode(codec)
        except UnicodeDecodeError as error:
            return self.send_response(Error.POSTINGFAILED + ': unable to '
                                      'decode: %s' % str(error))

        hdr = dict(zip(parsed.keys(), parsed.values()))
        msg = Msg(
            None,
            hdr.get('subject', 'no subject'),
            body,
        )
        msg.author = self.auth_username
        msg.tags.add(tag)
        msg.save()
        self.send_response(Status.POSTSUCCESSFULL)

    def do_QUIT(self):
        self.terminated = True
        self.send_response(Status.CLOSING)

    def do_SLAVE(self):
        self.send_response(Status.SLAVE)

    def do_STARTTLS(self):
        has_ssl = False
        try:
            has_ssl = ini.CFG.getboolean('nntp', 'ssl')
            ssl_crt = ini.CFG.get('nntp', 'cert')
            ssl_key = ini.CFG.get('nntp', 'key')
        except:
            pass

        if not has_ssl or ssl is None:
            return self.send_response(Error.CANTINITTLS)

        self.send_response(Status.CONTINUEWITHTLS)
        self.connection = ssl.wrap_socket(
            self.connection,
            server_side=True,
            keyfile=ssl_key,
            certfile=ssl_crt,
        )

    def do_XHDR(self):
        if (len(self.tokens) < 2) or (len(self.tokens) > 3):
            return self.send_response(Error.CMDSYNTAXERROR)

        if self.selected_group == 'ggg':
            return self.send_response(Error.NOGROUPSELECTED)

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

    def do_XROVER(self):
        self.tokens[1] = 'REFERENCES'
        return self.do_XHDR()


def start():
    import logging
    logger = logging.getLogger()

    t = Thread(target=server_thread)
    t.daemon = True
    t.start()
    logger.info(u'NNTP Server starting')

    has_ssl = False
    try:
        has_ssl = ini.CFG.getboolean('nntp', 'ssl')
        ssl_crt = ini.CFG.get('nntp', 'cert')
        ssl_key = ini.CFG.get('nntp', 'key')
    except:
        pass

    if has_ssl and not ssl is None:
        t = Thread(target=server_thread_ssl)
        t.daemon = True
        t.start()
        logger.info(u'NNTP Server starting (SSL)')


def setup_pipes():
    pass


def server_thread():
    addr = ini.CFG.get('nntp', 'addr')
    port = ini.CFG.getint('nntp', 'port')
    server = NNTPServer((addr, port), NNTPHandler)
    server.serve_forever()

def server_thread_ssl():
    addr = ini.CFG.get('nntp', 'ssl_addr')
    port = ini.CFG.getint('nntp', 'ssl_port')
    ssl_cert = ini.CFG.get('nntp', 'cert')
    ssl_key = ini.CFG.get('nntp', 'key')
    server = NNTPSServer(
        (addr, port),
        NNTPHandler,
        ssl_cert=ssl_cert,
        ssl_key=ssl_key,
    )
    server.serve_forever()
