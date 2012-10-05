"""
Simply call init. a multiprocessing.Pipe() parent end is returned.
For authorization, a tuple of ('db-userbase', (method, args) will be sent by
the child pipe. the parent pipe is expected to send a tuple of form:
  ('db-userbase', db['userbase'].method (*args))

  for integration with X/84 BBS software. A 3-year old request from zIPE
"""
import multiprocessing
from pyftpdlib import ftpserver
from bbs.dbproxy import DBProxy
from bbs import ini
import logging
logger = logging.getLogger(__name__)
logger.setLevel (logging.DEBUG)
ftpserver.logerror = logger.error
ftpserver.log = logger.info
ftpserver.logline = logger.debug

def main(pipe):
  import bbs.userbase
  IPCDB_TIMEOUT = 5.0

  def _sendfunc(event, data):
    pipe.send ((event, data,))

  def _recvfunc(events):
    if pipe.poll (IPCDB_TIMEOUT):
      ev, data = pipe.recv()
      assert ev in events
      return data

  class Throttler(ftpserver.ThrottledDTPHandler):
    read_limit = int(ini.cfg.get('ftp', 'read_limit'))
    write_limit = int(ini.cfg.get('ftp', 'write_limit'))

  class BBSFTPServer(ftpserver.FTPServer):
    max_cons = int(ini.cfg.get('ftp', 'conns_max'))
    max_cons_per_ip = int(ini.cfg.get('ftp', 'conns_per_ip'))

  class BBSFS(ftpserver.AbstractedFS):
    def __init__(self, root, cmd_channel):
      root = ini.cfg.get('ftp', 'basedir')
      ftpserver.AbstractedFS

  class BBSFTPHandler(ftpserver.FTPHandler):
    dtp_handler = Throttler
    banner = 'x/84 pyftpdlib %s ready.' % (ftpserver.__ver__,)
    timeout = int(ini.cfg.get('ftp', 'timeout'))
    permit_foreign_addresses = ini.cfg.get('ftp', 'enable_fxp') == 'yes'
    (_low, _high) = ini.cfg.get('ftp', 'pasv_ports').split('-',1)
    passive_ports = range(int(_low), int(_high))
    masquerade_address = ini.cfg.get('ftp', 'masq_addr') \
      if ini.cfg.get('ftp', 'enable_masquerade') == 'yes' else None

    def on_login(self, username):
      pipe.send (('global', ('ftp', ('login', username,))))

    def on_logout(self, username):
      pipe.send (('global', ('ftp', ('logout', username,))))

    def on_file_sent(self, file):
      pipe.send (('global', ('ftp', ('sent', file,))))

    def on_file_received(self, file):
      pipe.send (('global', ('ftp', ('recv', file,))))

    def on_incompile_file_sent(self, file):
      pipe.send (('global', ('ftp', ('sent-incomplete', file,))))

    def on_incompile_file_recv(self, file):
      pipe.send (('global', ('ftp', ('recv-incomplete', file,))))

  class BBSAuthorizer(ftpserver.DummyAuthorizer):
    db = None

    def __init__(self):
      ftpserver.DummyAuthorizer.__init__(self)

    def validate_authentication(self, username, password):
      if self.db is None:
        self.db = DBProxy(schema='userbase', send_f=_sendfunc, recv_f=_recvfunc)
      if not self.db.has_key(username):
        logger.info ('%s denied: user does not exist', username)
        return False
      u = self.db[username]
      if bbs.userbase.auth(u, password.decode('utf8')):
        if not username in self.user_table:
          self.add_user (username, password=u'', homedir=ini.cfg.get('ftp','basedir'))
        logger.info ('%s succeded login', username)
        for (directory, perms) in u.get('ftpoperms', ()):
          self.ovveride_perm(username, directory, perms, recursive=True)
        return True
      logger.warn ('%s denied: bad password', username)
      return False

    #def has_perm(username, permission, path):
    #  override_perm(self, username, directory, perm, recursive=False):

  handler = BBSFTPHandler
  handler.authorizer = BBSAuthorizer()
  if ini.cfg.get('ftp', 'enable_anonymous') == 'yes':
    authorizer.add_user ('anonymous', password=u'', homedir=ini.cfg.get('ftp','basedir'))
  address = (ini.cfg.get('ftp', 'addr'), int(ini.cfg.get('ftp', 'port')))
  server = BBSFTPServer(address, handler)
  logger.info ('[ftp:%s] listening tcp', address[1])
  server.serve_forever ()

def init():
  parent_conn, child_conn = multiprocessing.Pipe()
  p = multiprocessing.Process (target=main, args=(child_conn,))
  p.start ()
  return parent_conn
