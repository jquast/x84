""" Tetris game for x/84, https://github.com/jquast/x84 """
__author__ = 'Johannes Lundberg'
__copyright__ = 'Copyright 2007-2013'
__license__ = 'Public Domain'
# Single player tetris, originally written for The Progressive (prsv)
# Copyright (C) 2007-2013 Johannes Lundberg

def main():
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    assert term.width >= 79 and term.height >= 23
# intermediary fix ;/
    from x84.bbs import DBProxy
    db = DBProxy('tetris')
    for handle, score in db.items()[:]:
        if type(score) is int:
            del db[handle]
# delete me
    with term.hidden_cursor():
        score = play()
        if score[0] > 0:
            register_score(session.user.handle, score)
        show_scores(score)


def register_score(handle, score):
    from x84.bbs import DBProxy
    db = DBProxy('tetris')
    if not handle in db:
        db[handle] = score
    elif score[0] > db[handle][0]:
            db[handle] = score


def show_scores(my_score):
    from x84.bbs import DBProxy, Pager, getterminal
    from x84.bbs import getch, echo, getsession, ini
    session, term = getsession(), getterminal()
    scores = sorted(
            [ (_score, _level, _handle)
                for (_handle, (_score, _level, _lines))
                    in DBProxy('tetris').items()],
            reverse=True)
    if not len(scores):
        return
    handle_len = ini.CFG.getint('nua', 'max_user')
    score_len = 10
    score_fmt = '%-' + str(score_len) + 's %-2s %' + str(handle_len) + 's'


    # line up over tetris game, but logo & 'made by jojo' in view
    # -- since we have so much screen width, columize the scores,
    # looks like the math brings it out to 2 or 3 columns.
    height = 11
    width = 73
    yloc = 10
    xloc = 3
    pager = Pager(height=height, width=width, yloc=yloc, xloc=xloc)
    pager.xpadding = 1
    pager.glyphs['left-vert'] = u''
    pager.glyphs['right-vert'] = u''
    pager.colors['border'] = term.blue_reverse
    pager.alignment = 'center'
    def ismine(col):
        return col.split() == [str(my_score[0]), str(my_score[1]),
                session.user.handle]
    column_len = len(score_fmt % (u'', u'', u'',))
    columns = pager.visible_width / column_len
    def split_seq(seq, p):
        # http://code.activestate.com/recipes/425397-split-a-list-into-roughly-equal-sized-pieces/#c3
        newseq = []
        n = len(seq) / p    # min items per subsequence
        r = len(seq) % p    # remaindered items
        b,e = 0, n + min(1, r)  # first split
        for i in range(p):
            newseq.append(seq[b:e])
            r = max(0, r-1)  # use up remainders
            b,e = e, e + n + min(1, r)  # min(1,r) is always 0 or 1
        return newseq

    # do not columnize until we have at least that many records !
    if len(scores) > columns:
        score_txt = zip(*split_seq(
            [score_fmt % record for record in scores], columns))
    else:
        columns = len(scores)
        score_txt = [[score_fmt % record for record in scores]]

    spacer = u' ' * ((pager.visible_width - (column_len * columns))/columns)
    pager.append(spacer.join([score_fmt % (
        term.bold_blue_underline('SCORE'.ljust(score_len)),
        term.bold_blue_underline('lV')+ u' ',
        term.bold_blue_underline('hANdlE'.rjust(handle_len),))] * columns))
    empty_slot = u''.join((
        term.bold_black('.'.ljust(score_len + 1)),
        term.bold_black('.'.ljust(3)),
        term.bold_black('.'.rjust(handle_len))))
    # display scores, bold our in blue, if any,
    # fill additional columns with '.'
    for row in score_txt:
        pager.append(spacer.join(
            [col if not ismine(col)
            else term.bold_blue(col) for col in row]
            + [empty_slot] * (columns - len(row))))
    # append additional empty slot rows
    while len(pager.content) < pager.visible_height:
        pager.append(spacer.join([empty_slot] * columns))

    dirty = True
    while True:
        inp = getch(1)
        if inp in ('q', 'Q'):
            break
        dirty = True if session.poll_event('refresh') else dirty
        if dirty:
            echo(u''.join((
                pager.border(),
                pager.title(term.blue_reverse_underline('- hiGh SCOREs -')),
                term.normal,
                pager.refresh(),
                pager.footer(u''.join((
                    term.underline_blue('q'),
                    term.bold_blue('uit')))),
                )))
            dirty = False


def play():
    import time
    from random import randint
    import os
    from x84.bbs import getterminal, getch, from_cp437, AnsiWindow
    from x84.bbs import echo as echo_unbuffered
    term = getterminal()
    field = []
    global charcache
    charcache = u''
    field_width = 10
    field_height = 20
    # Access scheme looks like this:
    #   layout[p][r][ypox][xpos]
    # layoutcolor = [ 7,2,3,4,4,6,7 ]
    layout = [
        #  ##
        #  ##
        [
        [
        [1, 1, ],
        [1, 1, ],
        ],
        ],
        #  #
        #  #
        #  #
        #  #
        [
        [
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        ],
            [
                [0, 0, 0, 0],
                [1, 1, 1, 1],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]
        ],
        #  ###
        #   #
        [
        [
        [0, 0, 0],
        [1, 1, 1],
        [0, 1, 0],
        ],
            [
                [0, 1, 0],
                [0, 1, 1],
                [0, 1, 0],
            ],
            [
                [0, 1, 0],
                [1, 1, 1],
                [0, 0, 0],
            ],
            [
                [0, 1, 0],
                [1, 1, 0],
                [0, 1, 0],
            ],
        ],
        #  #
        #  #
        #  ##
        [
            [
                [0, 1, 0],
                [0, 1, 0],
                [0, 1, 1],
            ],
            [
                [0, 0, 1],
                [1, 1, 1],
                [0, 0, 0],
            ],
            [
                [1, 1, 0],
                [0, 1, 0],
                [0, 1, 0],
            ],
            [
                [0, 0, 0],
                [1, 1, 1],
                [1, 0, 0],
    ],
            ],
    #   #
    #   #
    #  ##
    [
            [
                [0, 1, 0],
                [0, 1, 0],
                [1, 1, 0],
                ],
            [
                [0, 0, 0],
                [1, 1, 1],
                [0, 0, 1],
                ],
            [
                [0, 1, 1],
                [0, 1, 0],
                [0, 1, 0],
                ],
            [
                [1, 0, 0],
                [1, 1, 1],
                [0, 0, 0],
                ],
            ],
    #  ##
    #   ##
    [
            [
                [0, 1, 0],
                [1, 1, 0],
                [1, 0, 0],
                ],
            [
                [0, 0, 0],
                [1, 1, 0],
                [0, 1, 1],
                ],
            ],
    #   ##
    #  ##
    [
            [
                [0, 1, 0],
                [0, 1, 1],
                [0, 0, 1],
                ],
            [
                [0, 0, 0],
                [0, 1, 1],
                [1, 1, 0],
                ],
            ],
    ]

    fieldx1 = 32
    fieldy1 = 10
    scorex1 = 11
    scorey1 = 11

    class RectRedraw:
        x1 = None
        y1 = None
        x2 = None
        y2 = None

        def max(r, val, valmax):
            if val > valmax:
                return valmax
            return val

        def min(r, val, valmin):
            if val < valmin:
                return valmin
            return val

        def merge(r, x1, y1, x2, y2):
            if r.x1 == None or r.x1 > x1:
                r.x1 = r.min(x1, 0)
            if r.y1 == None or r.y1 > y1:
                r.y1 = r.min(y1, 0)
            if r.x2 == None or r.x2 < x2:
                r.x2 = r.max(x2, field_width)
            if r.y2 == None or r.y2 < y2:
                r.y2 = r.max(y2, field_height)
            # print r.x1,r.y1,r.x2,r.y2

        def clean(r):
            r.x1 = None
            r.y1 = None
            r.x2 = None
            r.y2 = None
    rr = RectRedraw()
    for i in range(field_height):
        field.append([0] * field_width)

    def echo(s):
        global charcache
        charcache += s
    assert term.height > (field_height + 1)
    echo_unbuffered(u''.join((
        u'\r\n\r\n',
        u'REAdY YOUR tERMiNAl %s ' % (term.bold_blue('(!)'),),
        u'\r\n\r\n',
        u'%s PRESS ANY kEY' % (term.bold_black('...'),),
        )))
    getch()
    artfile = os.path.join(os.path.dirname(__file__), 'tetris.ans')
    echo_unbuffered(u'\r\n' * term.height)  # cls
    if os.path.exists(artfile):
        echo_unbuffered(from_cp437(open(artfile).read()).rstrip())

    def gotoxy(x, y):
        echo(term.move(y, x))

    def plotblock(color, lastcolor):
        if color:
            c = u'\u2588\u2588'  # '\xDB\xDB'
        else:  # both empty
            c = '  '
            color = 0
        # Output optimization
        if color % 8 == 0:
            color = color / 8
        if color == lastcolor:
            echo(c)
        else:
            if color:
                fg = str(30 + color % 8)
            else:
                fg = '37'
            if color >= 8:
                bg = ';%d' % (40 + color / 8)
            else:
                bg = ''
            echo('\33[0;' + fg + bg + 'm')
            echo(c)
            lastcolor = color
        return lastcolor

    def redrawfieldbig(rr):
        # rr.merge(0,0,field_width,field_height)
        lastcolor = ''
        if rr.x1 == None or rr.y1 == None:
            return
        # Only draw the parts which have been marked by the
        # redraw rectangle
        for y in range(rr.y1, rr.y2):
            gotoxy(field_width + rr.x1 * 2, 2 + y)
            for x in range(rr.x1, rr.x2):
                lastcolor = plotblock(field[y][x], lastcolor)
        echo(term.normal)
        rr.clean()

    def drawfieldbig():
        lastcolor = ''
        for y in range(0, field_height):
            gotoxy(field_width, 2 + y)
            for x in range(field_width):
                lastcolor = plotblock(field[y][x], lastcolor)
        echo(term.normal)

    def drawfield():
        lastcolor = ''
        for y in range(0, field_height, 2):
            # gotoxy(field_width,2+y/2)
            gotoxy(fieldx1 + 2, fieldy1 + 1 + y / 2)
            # Which block to show, full, half-up, half-down or empty.
            for x in range(field_width):
                color = field[y][x] + field[y + 1][x] * 8
                if field[y][x] and field[y + 1][x]:
                    c = u'\u2588'  # '\xDB'
                    if field[y][x] == field[y + 1][x]:
                        color = color % 8
                    else:
                        c = u'\u2580'  # '\xDF'
                elif field[y][x] and not field[y + 1][x]:
                    c = u'\u2580'  # '\xDF'
                elif not field[y][x] and field[y + 1][x]:
                    c = u'\u2584'  # '\xDC'
                else:  # both empty
                    c = ' '
                # Output optimization
                if color % 8 == 0:
                    color = color / 8
                if color == lastcolor:
                    echo(c)
                else:
                    if color:
                        fg = str(30 + color % 8)
                    else:
                        fg = '37'
                    if color >= 8:
                        bg = ';%d' % (40 + color / 8)
                    else:
                        bg = ''
                    echo('\33[0;' + fg + bg + 'm')
                    echo(c)
                    lastcolor = color
        echo(term.normal)

    layoutcolor = [7, 2, 7, 6, 3, 6, 3]
    # p    = -1  # Current piece type
    nextpiece = randint(0, len(layout) - 1)
    p = randint(0, len(layout) - 1)
    p = 1
    r = 0   # Current rotation
    xpos = 4   # X position
    # ypos = -2  # Y position
    ypos = -len(layout[p][0])
    level = 1
    score = 0
    lines = 0

    def flush():
        global charcache
        echo_unbuffered(charcache)
        charcache = u''

    def fillpiece(x, y, p, r, value):
        row = 0
        for line in layout[p][r]:
            col = 0
            for c in line:
                if c and (y + row) >= 0:
                    field[y + row][x + col] = value
                col += 1
            row += 1

    def showpiece(x, y, p, r):
        fillpiece(x, y, p, r, layoutcolor[p])

    def hidepiece():
        fillpiece(xpos, ypos, p, r, 0)

    def testpiece(x, y, newr):
        hidepiece()
        # Space at the new location?
        row = 0
        for line in layout[p][newr]:
            col = 0
            for c in line:
                try:
                    if (y + row) >= 0 and c:
                        if (field[y + row][x + col]
                                or (x + col) < 0 or (x + col) > 9):
                            return 0
                except IndexError:
                    return 0
                col += 1
            row += 1
        # Movement possible
        return 1

    def movepiece(x, y, newr):
        if testpiece(x, y, newr):
            # Build redraw rectangle
            rr.merge(xpos, ypos,
                     xpos + len(layout[p][0][0]), ypos + len(layout[p][0]))
            rr.merge(x, y,
                     x + len(layout[p][0][0]), y + len(layout[p][0]))
            showpiece(x, y, p, newr)
            return (x, y, newr, 1)
        else:
            showpiece(xpos, ypos, p, r)
            return (xpos, ypos, r, 0)

    def shownext(p):
        r = 0
        lastcolor = ''
        for y in range(6):
            gotoxy(38, 1 + y)
            for x in range(6):
                if y == 0 or y == 5 or x == 0 or x == 5:
                    echo('\xB0\xB0')
                else:
                    echo('\33[0m  ')
                    lastcolor = ''
        for y in range(len(layout[p][r])):
            gotoxy(40, 2 + y)
            for x in range(len(layout[p][r][0])):
                # plotblock(layoutcolor[layout[p][r][y][x]],lastcolor)
                plotblock(layout[p][r][y][x], lastcolor)

    def drawstats():
        echo(term.move(scorey1, scorex1) + '%d' % level)
        echo(term.move(scorey1 + 2, scorex1) + '%d' % lines)
        echo(term.move(scorey1 + 3, scorex1) + '%d' % score)

    drawstats()
    ticksize = 0.4
    nexttick = time.time() + ticksize
    showpiece(xpos, ypos, p, r)
    # shownext(nextpiece)

    # Full redraw first frame
    rr.merge(0, 0, field_width, field_height)

    buf = ''
    while 1:
        drawfield()
        # gotoxy(0,0)
        # echo('\33[37mx: %d, y: %d, p: %d         '%(xpos,ypos,p))
        slice = nexttick - time.time()
        if slice < 0:
            slice = 0
        echo(buf)
        buf = ''
        flush()
        key = getch(slice + 0.01)
        now = time.time()
        # hidepiece()
        if key is not None:
            if key in (u'q', u'Q'):
                return 0,0,0
            elif key in (u'S',):
                show_scores ((score, level, lines))
            elif key in (term.KEY_LEFT, u'h',):
                xpos, ypos, r, m = movepiece(xpos - 1, ypos, r)
            elif key in (term.KEY_RIGHT, u'l',):
                xpos, ypos, r, m = movepiece(xpos + 1, ypos, r)
            elif key in (term.KEY_UP, u'k',):
                xpos, ypos, r, m = movepiece(
                    xpos, ypos, (r + 1) % len(layout[p]))
            elif key in (term.KEY_DOWN, 'j',):
                xpos, ypos, r, m = movepiece(xpos, ypos + 1, r)
            elif key in (' ',):
                m = True
                c = 0
                while m:
                    xpos, ypos, r, m = movepiece(xpos, ypos + 1, r)
                    if m:
                        c += 1
                if c:
                    nexttick = time.time() + ticksize
        # New tick?
        if now > nexttick:
            nexttick += ticksize
            # Move down piece
            xpos, ypos, r, moved = movepiece(xpos, ypos + 1, r)
            # Piece has touched down?
            if not moved:
                # Is the player dead?
                if ypos <= -len(layout[p][0]):
                    death_win = AnsiWindow(height=6, width=40,
                        yloc=fieldy1 + 10 / 2, xloc=fieldx1 - 11)
                    death_win.colors['border'] = term.bold_black
                    echo_unbuffered(death_win.clear() + death_win.border())
                    echo_unbuffered(
                        term.move(fieldy1 + 10 / 2 + 1, fieldx1 - 11))
                    echo_unbuffered((
                      u'!! gAME OVeR!! Score was: %i' % (score,)).center(40))
                    echo_unbuffered(
                        term.move(fieldy1 + 10 / 2 + 3, fieldx1 - 11))
                    echo_unbuffered(u'press RETURN'.center(40))
                    while True:
                        inp = getch()
                        if inp in (u'\r', term.KEY_ENTER):
                            break
                    return (score, level, lines)

                # Any complete rows to remove?
                complete = []
                for y in range(field_height):
                    x = 0
                    while x < field_width:
                        if field[y][x] == 0:
                            break
                        x += 1
                    if x == field_width:
                        complete.append(y)
                if len(complete) > 0:
                    # Add score
                    lines += len(complete)
                    score += len(complete) * len(complete) * 100
                    # Shrink field
                    for line in complete:
                        del field[line]
                        field.insert(0, [0] * field_width)

                    if lines >= level * 10:
                        level += 1
                        ticksize = 0.4 - level * 0.02
                    drawstats()

                    # Redraw complete field
                    rr.merge(0, 0, field_width, field_height)

                # Time for a new piece
                p = nextpiece
                nextpiece = randint(0, len(layout) - 1)
                r = 0
                xpos = 4
                ypos = -len(layout[p][0])
                showpiece(xpos, ypos, p, r)
