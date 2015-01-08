#!/usr/bin/env python
def main():
    """
    Displays all known key capabilities that may match the terminal.
    As each key is pressed on input, it is lit up and points are scored.
    """
    try:
        from x84.bbs import getterminal, echo
        term = getterminal()
    except (ImportError, AttributeError):
        from blessed import Terminal
        import sys
        term = Terminal()

        def echo(text):
            sys.stdout.write(u'{}'.format(text))
            sys.stdout.flush()

    echo(u''.join((term.normal,
                   term.height * u'\r\n',
                   term.home,
                   term.clear_eos)))

    with term.raw():
        inp = u''
        echo(u'Press Q to exit.\r\n')
        while inp.upper() != 'Q':
            inp = term.inkey(timeout=10.0)
            disp_inp = inp.__str__() if inp.is_sequence else inp
            echo(u'{0!r}: code={1!r} name={2!r}\r\n'
                 .format(disp_inp, inp.code, inp.name))

if __name__ == '__main__':
    main()
