"""
Logging handler for x/84 BBS, http://github.com/jquast/x84
"""
import logging
import copy
import sys
from blessed import Terminal


class ColoredConsoleHandler(logging.StreamHandler):
    """
    A stream handler that colors the levelname, thats all.
    """

    def __init__(self):
        """ Constructor class, initializes blessings Terminal. """
        self.term = Terminal(stream=sys.stderr)
        logging.StreamHandler.__init__(self)

    def color_levelname(self, record):
        """ Modify levelname field to include terminal color sequences.  """
        record.levelname = (self.term.bold_red if record.levelno >= 50 else
                            self.term.bold_red if record.levelno >= 40 else
                            self.term.bold_yellow if record.levelno >= 30 else
                            self.term.bold_white if record.levelno >= 20 else
                            self.term.blue)('%-5s' % (
                                record.levelname.title()
                                if record.levelname.lower() != 'warning'
                                else 'warn',))
        return record

    def transform(self, src_record):
        """ Return a modified log record """
        return self.color_levelname(src_record)

    def emit(self, src_record):
        """ Emit record to console """
        # transform
        dst_record = self.transform(copy.copy(src_record))

        # emit to console
        logging.StreamHandler.emit(self, dst_record)
