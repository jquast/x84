""" File transfer routines for x/84. """

# local imports
from x84.bbs.session import getsession

# 3rd party
import xmodem


def send_modem(stream, protocol='xmodem1k', retry=16, timeout=30,
               callback=None):
    """
    Send a file using 'xmodem1k' or 'xmodem' protocol.

    Currently, these are the only protocols supported.  Returns ``True`` upon
    successful transmission, otherwise ``False``.

    :param stream: The file-like stream object to send data from.
    :param int retry: The maximum number of times to try to resend a failed
                      packet before failing.
    :param int timeout: seconds to elapse for response before failing.
    :param callable callback: Reference to a callback function that has the
           following signature. This is useful for getting
           status updates while a transfer is underway::

               def callback(total_count, success_count, error_count)
    """
    # get protocol implementation class
    supported_protocols = ('xmodem', 'xmodem1k')
    assert protocol in supported_protocols, (protocol, supported_protocols)
    Modem = {
        'xmodem': xmodem.XMODEM,
        'xmodem1k': xmodem.XMODEM1k,
    }[protocol]

    # the session's 'input' event buffer is used for receiving
    # transmissions.  It arrives in raw bytes, and session.write
    # is used, sending "unicode" data as encoding iso8859-1.
    session = getsession()

    def getc(size, timeout=10):
        """ Callback function for (X)Modem interface. """
        val = b''
        while len(val) < size:
            next_val = session.read_event('input', timeout=timeout)
            if next_val is None:
                break
            val += next_val
        if len(val) > size:
            session.buffer_input(val[size:])
        return val[:size] or None

    def putc(data, timeout=10):
        # pylint: disable=W0613
        #         Unused argument 'timeout'
        """ Callback function for (X)Modem interface. """
        session.write(data.decode('iso8859-1'), 'iso8859-1')

    modem = Modem(getc, putc)
    return modem.send(stream=stream, retry=retry, timeout=timeout,
                      quiet=True, callback=callback)


def recv_modem(stream, protocol='xmodem1k', retry=16, timeout=30):
    """
    Receive a file using 'xmodem1k' or 'xmodem' protocol into ``stream``.

    Currently, these are the only protocols supported.  Returns ``True`` upon
    successful transmission, otherwise ``False``.

    :param stream: The file-like stream object to send data from.
    :param int retry: The maximum number of times to try to resend a failed
                      packet before failing.
    :param int timeout: seconds to elapse for response before failing.
    """
    # get protocol implementation class
    supported_protocols = ('xmodem', 'xmodem1k')
    assert protocol in supported_protocols, (protocol, supported_protocols)
    Modem = {
        'xmodem': xmodem.XMODEM,
        'xmodem1k': xmodem.XMODEM1k,
    }[protocol]

    # the session's 'input' event buffer is used for receiving
    # transmissions.  It arrives in raw bytes, and session.write
    # is used, sending "unicode" data as encoding iso8859-1.
    session = getsession()

    def getc(size, timeout=10):
        """ Callback function for (X)Modem interface. """
        val = b''
        while len(val) < size:
            next_val = session.read_event('input', timeout=timeout)
            if next_val is None:
                break
            val += next_val
        if len(val) > size:
            session.buffer_input(val[size:])
        return val[:size] or None

    def putc(data, timeout=10):
        """ Callback function for (X)Modem interface. """
        # pylint: disable=W0613
        #         Unused argument 'timeout'
        session.write(data.decode('iso8859-1'), 'iso8859-1')

    modem = Modem(getc, putc)
    return modem.recv(stream=stream, retry=retry,
                      timeout=timeout, quiet=True)
