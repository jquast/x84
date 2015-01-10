""" Session IPC for x/84. """
# std imports
import logging

# local
from x84.bbs.session import getsession


def make_root_logger(out_queue):
    """
    Remove any existing handlers of the current process, and
    re-address the root logging handler to an IPC output event queue
    """
    root = logging.getLogger()
    map(root.removeHandler, root.handlers)
    root.addHandler(IPCLogHandler(out_queue=out_queue))


class IPCLogHandler(logging.Handler):

    """
    Log handler that sends the log up the 'event pipe'. This is a rather novel
    solution that seems overlooked in documentation or exisiting code, try it!
    """
    _session = None

    def __init__(self, out_queue):
        """ Constructor method, requires multiprocessing.Pipe """
        logging.Handler.__init__(self)
        self.oqueue = out_queue

    def emit(self, record):
        """ emit log record via IPC output queue. """
        try:
            e_inf = record.exc_info
            if e_inf:
                # a strange side-effect,
                # sets record.exc_text
                dummy = self.format(record)  # NOQA
                record.exc_info = None
            record.handle = None
            record.handle = getsession().handle
            self.oqueue.send(('logger', record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class IPCStream(object):

    """
    Connect blessed.Terminal argument 'stream' to 'writer' queue, a
    ``multiprocessing.Pipe`` whose master-side is polled for output
    in x84.engine.

    Only the write() method of this "stream" is called by blessed.
    """

    def __init__(self, writer):
        self.writer = writer
        self.is_a_tty = True

    def write(self, ucs, encoding='ascii'):
        """
        Sends unicode text to Pipe.

        Default encoding is 'ascii', which is unset only when used
        with blessings, which rarely writes directly to the stream
        (context managers, such as "with term.location(0, 0):" have
        such side effects).
        """
        # wrap 'ucs' with call to 'unicode()', so that special unicode
        # instances such as blessed.formatters.ParameterizingProxyString
        # can be pickled -- as this one in particular contains a local
        # function (lambda) as an attribute -- which would fail:
        # PicklingError: Can't pickle <type 'function'>: attribute
        #                lookup __builtin__.function failed
        self.writer.send(('output', (unicode(ucs), encoding)))
