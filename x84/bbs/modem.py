# 3rd party library
import xmodem


def send_modem(stream, protocol='xmodem1k', retry=16, timeout=30,
               callback=None):
    """
    Send a file using 'xmodem1k' or 'xmodem' protocol.

    Currently, these are the only protocols supported.  Returns ``True`` upon
    successful transmission, otherwise ``False``.

    :param stream: The stream object to send data from.
    :type stream: stream (file, etc.)
    :param retry: The maximum number of times to try to resend a failed
                  packet before failing.
    :type retry: int
    :param timeout: seconds to elapse for response before failing.
    :type timeout: int
    :param callback: Reference to a callback function that has the following
                     signature. This is useful for getting status updates while
                     a transfer is underway:
                     ``def callback(total_count, success_count, error_count)``
    :type callback: callable
    """
    from x84.bbs.session import getsession

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
        return session.read_event('input', timeout=timeout)

    def putc(data, timeout=10):
        session.write(data.decode('iso8859-1'), 'iso8859-1')

    modem = Modem(getc, putc)
    modem.send(stream=stream, retry=retry, timeout=timeout,
               quiet=True, callback=callback)
