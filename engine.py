#!/usr/bin/env python
"""
command-line launcher and main event loop for x/84
"""
# Please place _ALL_ Metadata here. No need to duplicate this
# in every .py file of the project -- except where individual scripts
# are authored by someone other than the authors, licensing differs, etc.
__author__ = "Johannes Lundberg, Jeffrey Quast"
__copyright__ = "Copyright 2012"
__credits__ = ["Johannes Lundberg", "Jeffrey Quast",
               "Wijnand Modderman-Lenstra", "zipe", "spidy",
               "Mercyful Fate",]
__license__ = 'ISC'
__version__ = '1.0rc1'
__maintainer__ = 'Jeff Quast'
__email__ = 'dingo@1984.ws'
__status__ = 'Development'

import sys

def main ():
    """
    x84 main entry point. The system begins and ends here.

    Command line arguments to engine.py:
      -cfg: location of alternate configuration file
        -v: enable DEBUG logging
    """
    #pylint: disable=R0914
    #        Too many local variables (19/15)
    import logging
    import getopt
    import terminal
    import telnet
    import bbs
    import log
    logger = logging.getLogger(__name__)
    log_level = logging.INFO
    cfg_filepath = 'default.ini'
    try:
        opts, tail = getopt.getopt(sys.argv[1:], "vc:", ('verbose', 'config'))
    except getopt.GetoptError, err:
        sys.stderr.write ('%s\n' % (err,))
        return 1
    for opt, arg in opts:
        if opt in ('-v', '--verbose'):
            log_level = logging.DEBUG
        elif opt in ('-c', '--config'):
            cfg_filepath = arg
        else:
            assert False
    assert 0 == len (tail), 'Unrecognized program arguments: %s' % (tail,)
    logger.setLevel(log_level)
    log_handler = log.get_stderr(level=log_level)
#    if logger.isEnabledFor(logging.DEBUG):
#        import __builtin__
#        real_import = __builtin__.__import__
#        def debug_import(name, my_locals=None, my_globals=None,
#            fromlist=None, level=-1):
#            """ a replacement for import that prints who imports what,
#                from python documentation example. only enabled when
#                the logger is at DEBUG or higher
#            """
#            #pylint: disable=W0212
#            #        Access to a protected member _getframe of a client class
#            glob = my_globals or sys._getframe(1).f_globals
#            importer_name = glob and glob.get('__name__') or 'unknown'
#            logger.debug ('%s imports %s', importer_name, name)
#            return real_import(name, my_locals, my_globals, fromlist, level)
#        __builtin__.__import__ = debug_import

    terminal.logger.addHandler (log_handler)
    terminal.logger.setLevel (logger.level)
    logger.addHandler (log_handler)

    bbs.session.logger.addHandler (log_handler)
    bbs.session.logger.setLevel (logger.level)
    logger.addHandler (log_handler)

    sys.stdout.write ('x/84 bbs ')
    # load .ini file
    bbs.ini.init (cfg_filepath)

    # initialize scripting subsystem
    bbs.scripting.init (bbs.ini.cfg.get('session', 'scriptpath'))

    # initialize telnet server
    telnet.logger.setLevel (logger.level)
    telnet.logger.addHandler (log_handler)
    addr_tup = (bbs.ini.cfg.get('telnet', 'addr'),
        int(bbs.ini.cfg.get('telnet', 'port')),)
    telnet_server = telnet.TelnetServer (
        address_pair = addr_tup,
        on_connect = terminal.on_connect,
        on_disconnect = terminal.on_disconnect,
        on_naws = terminal.on_naws)
    logger.info ('[telnet:%s] listening tcp', telnet_server.port)

    # begin main event loop
    _loop(logger, telnet_server)

def _loop(logger, telnet_server):
    """ Main event loop. Never returns. """
    # pylint: disable=R0912
    #         Too many branches (15/12)
    import terminal
    import db
    # main event loop
    while True:
        # process telnet i/o
        telnet_server.poll()
        for client, pipe, lock in terminal.terminals():
            if not lock.acquire(False):
                continue
            lock.release ()

            # process telnet input (keypress sequences)
            if client.input_ready() and lock.acquire(False):
                lock.release()
                inp = client.get_input()
                pipe.send (('input', inp))

            if lock.acquire(False):
                # process bbs session i/o
                lock.release ()
                if not pipe.poll ():
                    continue

            try:
                # session i/o sent from child process
                event, data = pipe.recv()

            except EOFError:
                logger.error ('eof,')
                terminal.unregister_terminal (client, pipe, lock)
                continue

            if event == 'disconnect':
                client.deactivate ()

            elif event == 'output':
                text, is_cp437 = data
                if not is_cp437:
                    client.send_unicode (text)
                else: # text has already been 'translated' to the apropriate
                      # unichr(0)-unichr(255) as unicode -- encoding as
                      # 'iso8859-1' will byte values intact as chr(0)-chr(255)
                    bytestring = text.encode('iso8859-1', 'replace')
                    client.send_str (bytestring)

            elif event == 'global':
                #pylint: disable=W0612
                #         Unused variable 'o_lock'
                for o_client, o_pipe, o_lock in terminal.terminals():
                    if o_client == client:
                        o_pipe.send ((event, data,))

            elif event == 'pos':
                assert type(data) in (float, int, type(None))
                # assert 'timeout' parameter, 1, 1.0, or None
                # 'pos' query: 'what is the cursor position ?'
                # returns 'pos-reply' event as a callback
                # mechanism, data of (None, None) indicates timeout,
                # otherwise (y, x) is cursor position ..
                thread = terminal.POSHandler(pipe, client, lock,
                    reply_event='pos-reply', timeout=data)
                thread.start ()

            elif event.startswith ('db-'):
                # db query-> database dictionary method, callback
                # with a matching ('db-*',) event. sqlite is used
                # for now and is quick, but this prevents slow
                # database queries from locking the i/o event loop.
                thread = db.DBHandler(pipe, event, data)
                thread.start ()

if __name__ == '__main__':
    sys.exit(main ())
