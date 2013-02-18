"""
Session IPC for x/84, http://github.com/jquast/x84/
"""
import logging


class IPCLogHandler(logging.Handler):
    """
    Log handler that sends the log up the 'event pipe'. This is a rather novel
    solution that seems overlooked in documentation or exisiting code, try it!
    """
    def __init__(self, pipe):
        """ Constructor method, requires multiprocessing.Pipe """
        logging.Handler.__init__(self)
        self.pipe = pipe
        self.session = None

    def emit(self, record):
        """
        emit log record via IPC pipe
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
            self.pipe.send(('logger', record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class IPCStream(object):
    """
    Connect blessings 'stream' to 'child' multiprocessing.Pipe
    only write(), fileno(), and close() are called by blessings.
    """
    def __init__(self, channel):
        self.channel = channel

    def write(self, ucs, encoding):
        """
        Sends unicode text to Pipe.
        """
        self.channel.send(('output', (ucs, encoding)))

    def fileno(self):
        """
        Returns pipe fileno.
        """
        return self.channel.fileno()

    def close(self):
        """
        Closes pipe.
        """
        return self.channel.close()
