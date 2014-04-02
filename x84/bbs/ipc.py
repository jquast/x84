"""
Session IPC for x/84, http://github.com/jquast/x84/
"""
import logging


class IPCLogHandler(logging.Handler):
    """
    Log handler that sends the log up the 'event pipe'. This is a rather novel
    solution that seems overlooked in documentation or exisiting code, try it!
    """
    def __init__(self, out_queue):
        """ Constructor method, requires multiprocessing.Pipe """
        logging.Handler.__init__(self)
        self.oqueue = out_queue
        self.session = None

    def emit(self, record):
        """
        emit log record via IPC output queue
        """
        try:
            e_inf = record.exc_info
            if e_inf:
                # side-effect: sets record.exc_text
                dummy = self.format(record)
                record.exc_info = None
                # pylint: disable=W0104
                #         Statement seems to have no effect
                dummy  # pflakes ;/
            record.handle = (self.session.handle
                             if self.session is not None else None)
            if self.session is not None:
                self.session.lock.acquire()
            self.oqueue.send(('logger', record))
            if self.session is not None:
                self.session.lock.release()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class IPCStream(object):
    """
    Connect blessings 'stream' to 'child' output multiprocessing.Queue
    only write() is called by blessings.
    """
    # pylint: disable=R0903
    #         Too few public methods
    def __init__(self, out_queue, lock):
        self.oqueue = out_queue
        self.lock = lock
        self.is_a_tty = True

    def write(self, ucs, encoding='ascii'):
        """
        Sends unicode text to Pipe. Default encoding is 'ascii',
        which is unset only when used with blessings, which rarely
        writes directly to the stream (context managers, such as
        "with term.location(0, 0):" have such side effects).
        """
        self.lock.acquire()
        self.oqueue.send(('output', (ucs, encoding)))
        self.lock.release()
