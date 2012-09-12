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
      if bbs.userbase.auth(u, password.decode('utf-8')):
        if not username in self.user_table:
          self.add_user (username, password=u'', homedir=ini.cfg.get('ftp','basedir'))
        logger.info ('%s succeded login', username)
        return True
      logger.warn ('%s denied: bad password', username)
      return False

  handler = ftpserver.FTPHandler
  handler.authorizer = BBSAuthorizer()
  handler.banner = 'x/84 pyftpdlib %s ready.' % (ftpserver.__ver__,)
  # TODO add masquerade & passive port support
  address = (ini.cfg.get('ftp', 'addr'), int(ini.cfg.get('ftp', 'port')))
  server = ftpserver.FTPServer(address, handler)
  server.max_cons = 256
  server.max_cons_per_ip = 5
  server.serve_forever ()
  logger.info ('[ftp:%s] listening tcp', address[1])

def init():
  parent_conn, child_conn = multiprocessing.Pipe()
  p = multiprocessing.Process (target=main, args=(child_conn,))
  p.start ()
  return parent_conn
