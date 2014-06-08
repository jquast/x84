#!/usr/bin/env python
def main():
    """
    Displays all known key capabilities that may match the terminal.
    As each key is pressed on input, it is lit up and points are scored.
    """
    from x84.bbs import getterminal, echo
    term = getterminal()
    score = level = hit_highbit = hit_unicode = 0
    dirty = True

    def refresh(term, board, level, score, inp):
        echo(term.home + term.clear)
        level_color = level % 7
        if level_color == 0:
            level_color = 4
        bottom = 0
        for keycode, attr in board.items():
            echo(u''.join((
                term.move(attr['row'], attr['column']),
                term.color(level_color),
                (term.reverse if attr['hit'] else term.bold),
                keycode,
                term.normal)))
            bottom = max(bottom, attr['row'])
        echo(term.move(term.height, 0)
                         + 'level: %s score: %s' % (level, score,))
        sys.stdout.flush()
        if bottom >= (term.height - 5):
            echo(
                '\r\n' * (term.height / 2) +
                term.center(term.red_underline('cheater!')) + '\r\n')
            echo(
                term.center("(use a larger screen)") +
                '\r\n' * (term.height / 2))
            term.inkey()
            return
        for row, inp in enumerate(inps[(term.height - (bottom + 2)) * -1:]):
            echo(term.move(bottom + row+1))
            disp_inp = inp
            if inp.is_sequence:
                disp_inp = inp.__str__()
            echo(u'%{0!r} {1!r} {2!r}'.format(disp_inp, inp.code, inp.name))

    def build_gameboard(term):
        column, row = 0, 0
        board = dict()
        spacing = 2
        for keycode in sorted(term._keycodes.values()):
            if (keycode.startswith('KEY_F')
                    and keycode[-1].isdigit()
                    and int(keycode[len('KEY_F'):]) > 24):
                continue
            if column + len(keycode) + (spacing * 2) >= term.width:
                column = 0
                row += 1
            board[keycode] = {'column': column,
                              'row': row,
                              'hit': 0,
                              }
            column += len(keycode) + (spacing * 2)
        return board

    def add_score(score, pts, level):
        lvl_multiplier = 10
        score += pts
        if 0 == (score % (pts * lvl_multiplier)):
            level += 1
        return score, level

    gb = build_gameboard(term)
    inps = []

    with term.raw():
        inp = term.inkey(timeout=0)
        while inp.upper() != 'Q':
            if dirty:
                refresh(term, gb, level, score, inps)
                dirty = False
            inp = term.inkey(timeout=5.0)
            dirty = True
            if (inp.is_sequence and
                    inp.name in gb and
                    0 == gb[inp.name]['hit']):
                gb[inp.name]['hit'] = 1
                score, level = add_score(score, 100, level)
            elif inp and not inp.is_sequence and 128 <= ord(inp) <= 255:
                hit_highbit += 1
                if hit_highbit < 5:
                    score, level = add_score(score, 100, level)
            elif inp and not inp.is_sequence and ord(inp) > 256:
                hit_unicode += 1
                if hit_unicode < 5:
                    score, level = add_score(score, 100, level)
            inps.append(inp)

    with term.cbreak():
        echo(term.move(term.height))
        echo(
            u'{term.clear_eol}Your final score was {score} '
            u'at level {level}{term.clear_eol}\r\n'
            u'{term.clear_eol}\r\n'
            u'{term.clear_eol}You hit {hit_highbit} '
            u' 8-bit characters\r\n{term.clear_eol}\r\n'
            u'{term.clear_eol}You hit {hit_unicode} '
            u' unicode characters.\r\n{term.clear_eol}\r\n'
            u'{term.clear_eol}press any key\r\n'.format(
                term=term,
                score=score, level=level,
                hit_highbit=hit_highbit,
                hit_unicode=hit_unicode)
        )
        term.inkey()

if __name__ == '__main__':
    main()
