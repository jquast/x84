""" System info script for x/84. """


def main():
    """ Main procedure. """
    # pylint: disable=R0914,W0141,R0912
    #         Too many local variables
    #         Used builtin function 'map'
    #         Too many branches
    from x84.bbs import getsession, getterminal, echo, syncterm_setfont
    from x84.engine import __url__ as url
    import platform
    import random
    import sys
    import os
    session, term = getsession(), getterminal()
    session.activity = 'System Info'
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'plant.ans',)
    # pylint: disable=W0633
    #         Attempting to unpack a non-sequence defined at line 1160 of
    #         platform
    system, _, release, _, machine, _ = platform.uname()

    body = [u'authors:',
            u'Johannes Lundberg',
            u'Jeffrey Quast',
            u'Wijnand Modderman-Lenstra',
            u'',
            u'artwork:',
            u'hellbeard!impure',
            u'\r\n',
            u'system: %s %s %s' % (system, release, machine),
            u'software: x/84',
            url,
            u'\r\n',
            (platform.python_implementation() + u' '
                + '-'.join(map(str, sys.version_info[3:])))
            + u' ' + (platform.python_version()
                      if hasattr(platform, 'python_implementation')
                      else u'.'.join(map(str, sys.version_info[:3]))),
            ]
    melt_colors = (
        [term.normal]
        + [term.bold_blue] * 3
        + [term.red] * 4
        + [term.bold_red]
        + [term.bold_white]
        + [term.normal] * 6
        + [term.blue] * 2
        + [term.bold_blue]
        + [term.bold_white]
        + [term.normal])
    art = open(artfile).read().decode('cp437_art') \
        if os.path.exists(artfile) else u''
    otxt = list(art.splitlines())
    for num, line in enumerate(body):
        while num > len(otxt):
            otxt += [u'', ]
        otxt[num] = otxt[num][:int(term.width / 2.5)] + u' ' + line
    width = max([term.length(line) for line in otxt])
    height = len(otxt)
    num_stars = int((term.width * term.height) * .005)
    stars = dict([(n, (random.choice('\\|/-'),
                       float(random.choice(range(term.width))),
                       float(random.choice(range(term.height)))))
                  for n in range(num_stars)])
    melting = {}
    show_star = False
    tm_out, tm_min, tm_max, tm_step = 0.08, 0.01, 2.0, .01
    wind = (0.7, 0.1, 0.01, 0.01)

    def refresh():
        """ Refresh screen and return top-left (x, y) location. """
        # set syncterm font to cp437
        if term.kind.startswith('ansi'):
            echo(syncterm_setfont('cp437'))
        echo(u'\r\n\r\n')
        if term.width < width:
            echo(u''.join((
                term.move(term.height, 0),
                u'\r\n\r\n',
                term.bold_red + 'screen too thin! (%s/%s)' % (
                    term.width, width,),
                u'\r\n\r\n',
                u'press any key...',)))
            term.inkey()
            return (None, None)
        if term.height < height:
            echo(u''.join((
                term.move(term.height, 0),
                u'\r\n\r\n',
                term.bold_red + 'screen too short! (%s/%s)' % (
                    term.height, height),
                u'\r\n\r\n',
                u'press any key...',)))
            term.inkey()
            return (None, None)
        xloc = (term.width / 2) - (width / 2)
        yloc = (term.height / 2) - (height / 2)
        echo(u''.join((
            term.normal,
            (u'\r\n' + term.clear_eol) * term.height,
            u''.join([term.move(yloc + abs_y, xloc) + line
                      for abs_y, line in enumerate(otxt)]),)))
        return xloc, yloc

    txt_x, txt_y = refresh()
    if (txt_x, txt_y) == (None, None):
        return

    def char_at_pos(yloc, xloc, txt_y, txt_x):
        """ Return art (y, x) for location """
        return (u' ' if yloc - txt_y < 0 or yloc - txt_y >= height
                or xloc - txt_x < 0 or xloc - txt_x >= len(otxt[yloc - txt_y])
                else otxt[yloc - txt_y][xloc - txt_x])

    def iter_wind(xslope, yslope, xdir, ydir):
        """ An easterly Wind """
        xslope += xdir
        yslope += ydir
        if xslope <= 0.5:
            xdir = random.choice([0.01, 0.015, 0.02])
        elif xslope >= 1:
            xdir = random.choice([-0.01, -0.015, -0.02])
        if yslope <= -0.1:
            ydir = random.choice([0.01, 0.015, 0.02, 0.02])
        elif yslope >= 0.1:
            ydir = random.choice([-0.01, -0.015, -0.02])
        return xslope, yslope, xdir, ydir

    def iter_star(char, xloc, yloc):
        """ Given char and current position, apply wind and return new
        char and new position. """
        if char == '\\':
            char = '|'
        elif char == '|':
            char = '/'
        elif char == '/':
            char = '-'
        elif char == '-':
            char = '\\'
        xloc += wind[0]
        yloc += wind[1]
        if xloc < 1 or xloc > term.width:
            xloc = (1.0 if xloc > term.width
                    else float(term.width))
            yloc = (float(random.choice
                          (range(term.height))))
        if yloc < 1 or yloc > term.height:
            yloc = (1.0 if yloc > term.height
                    else float(term.height))
            xloc = (float(random.choice
                          (range(term.width))))
        return char, xloc, yloc

    def erase(star_idx):
        """ erase old star before moving .. """
        if show_star:
            _, xloc, yloc = stars[star_idx]
            echo(u''.join((term.move(int(yloc), int(xloc)), term.normal,
                           char_at_pos(int(yloc), int(xloc), txt_y, txt_x),)))

    def melt():
        """ Iterate through all stars and phase through melt sequence. """
        def melted(yloc, xloc):
            """ shift melt, delete if disappeared. """
            melting[(yloc, xloc)] -= 1
            if 0 == melting[(yloc, xloc)]:
                del melting[(yloc, xloc)]
        for (yloc, xloc), phase in melting.items():
            echo(u''.join((term.move(yloc, xloc), melt_colors[phase - 1],
                           char_at_pos(yloc, xloc, txt_y, txt_x),)))
            melted(yloc, xloc)

    def draw_star(star, xloc, yloc):
        """ draw star a (x, y) location """
        char = char_at_pos(int(yloc), int(xloc), txt_y, txt_x)
        if char != ' ':
            melting[(int(yloc), int(xloc))] = len(melt_colors)
        if show_star:
            echo(term.move(int(yloc), int(xloc)) + melt_colors[-1] + star)

    with term.hidden_cursor():

        while txt_x is not None and txt_y is not None:

            if session.poll_event('refresh'):
                num_stars = int(num_stars)
                stars = dict([(n, (random.choice('\\|/-'),
                                   float(random.choice(range(term.width))),
                                   float(random.choice(range(term.height)))))
                              for n in range(num_stars)])
                otxt = list(art.splitlines())
                for num, line in enumerate(body):
                    while num > len(otxt):
                        otxt += [u'', ]
                    otxt[num] = (otxt[num][:int(term.width / 2.5)]
                                 + u' ' + line)
                txt_x, txt_y = refresh()
                continue

            inp = term.inkey(tm_out)

            if inp.code == term.KEY_UP or inp.lower() == u'k':
                if tm_out >= tm_min:
                    tm_out -= tm_step
            elif inp.code == term.KEY_DOWN or inp.lower() == u'j':
                if tm_out <= tm_max:
                    tm_out += tm_step
            elif inp.code == term.KEY_LEFT or inp.lower() == u'h':
                if num_stars > 2:
                    num_stars = int(num_stars * .5)
                    stars = dict([(n, (random.choice('\\|/-'),
                                       float(random.choice(range(term.width))),
                                       float(random.choice(range(term.height)))
                                       )) for n in range(num_stars)])
            elif inp.code == term.KEY_RIGHT or inp.lower() == u'l':
                if num_stars < (term.width * term.height) / 4:
                    num_stars = int(num_stars * 1.5)
                    stars = dict([(n, (random.choice('\\|/-'),
                                       float(random.choice(range(term.width))),
                                       float(random.choice(range(term.height)))
                                       )) for n in range(num_stars)])
            elif inp in (u'*',):
                show_star = not show_star
                if not show_star:
                    for star in stars:
                        erase(star)
            elif inp:
                # any other key just exits, like a screen saver.
                echo(term.move(term.height, 0))
                break

            melt()

            for star_key, star_val in stars.items():
                erase(star_key)
                stars[star_key] = iter_star(*star_val)
                draw_star(*stars[star_key])

            wind = iter_wind(*wind)
