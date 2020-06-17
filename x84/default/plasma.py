#!/usr/bin/env python
# std imports
from __future__ import print_function, division
import sys
import math
import time
import timeit
import colorsys
import contextlib

# local
from x84.bbs import getsession, getterminal, echo

# 3rd party
import blessed
from backports.functools_lru_cache import lru_cache


def scale_255(val): return int(round(val * 255))

@lru_cache(maxsize=25000)
def squirt_xywh(x, y, w, h):
    return math.sqrt(
        ((x - w / 2.0) * (x - w / 2.0) +
         (y - h / 2.0) * (y - h / 2.0))
    ) / 8.0


def rgb_at_xy(term, x, y, t):
    h, w = term.height, term.width
    hue = 4.0 + (
        math.sin(x / 16.0)
        + math.sin(y / 32.0)
        + squirt_xywh(x, y, w, h) + t * 3
    ) + math.sin(math.sqrt((x * x + y * y)) / 8.0)
    saturation = y / h
    lightness = x / w
    return tuple(map(scale_255, colorsys.hsv_to_rgb(hue / 8.0, saturation, lightness)))


def screen_plasma(term, plasma_fn, t):
    result = ''
    for y in range(term.height - 1):
        for x in range(term.width):
            result += term.on_color_rgb(*plasma_fn(term, x, y, t)) + ' '
    return result


@contextlib.contextmanager
def elapsed_timer():
    """Timer pattern, from https://stackoverflow.com/a/30024601."""
    start = timeit.default_timer()

    def elapser():
        return timeit.default_timer() - start

    # pylint: disable=unnecessary-lambda
    yield lambda: elapser()


def show_please_wait(term):
    txt_wait = 'please wait ...'
    outp = term.move_yx(term.height - 1, 0) + term.clear_eol + term.center(txt_wait)
    echo(outp)


def show_paused(term):
    txt_paused = 'paused'
    outp = term.move_yx(term.height - 1, int(term.width / 2 - len(txt_paused) / 2))
    outp += txt_paused
    echo(outp)


def next_algo(algo, forward):
    algos = tuple(sorted(blessed.color.COLOR_DISTANCE_ALGORITHMS))
    next_index = algos.index(algo) + (1 if forward else -1)
    if next_index == len(algos):
        next_index = 0
    return algos[next_index]


def next_color(color, forward):
    colorspaces = (4, 8, 16, 256, 1 << 24)
    next_index = colorspaces.index(color) + (1 if forward else -1)
    if next_index == len(colorspaces):
        next_index = 0
    return colorspaces[next_index]


def status(term, elapsed):
    left_txt = ('{term.number_of_colors} colors - '
                '{term.color_distance_algorithm} - ?: help '
                .format(term=term))
    fps = 1 / elapsed
    right_txt = 'fps: {0:2.3f}'.format(fps)
    return (term.normal +
            term.white_on_blue + term.clear_eol + left_txt +
            term.rjust(right_txt, term.width - len(left_txt)))


def main():
    session, term = getsession(), getterminal()
    session.activity = "Tripping out on colors!"
    term.color_distance_algorithm = 'rgb-weighted'

    with term.hidden_cursor(), term.fullscreen():
        pause, dirty = False, True
        t = time.time()
        while True:
            if dirty or not pause:
                if not pause:
                    t = time.time()
                with elapsed_timer() as elapsed:
                    outp = term.home + screen_plasma(term, rgb_at_xy, t)
                outp += status(term, elapsed())
                echo(outp)
                #assert False, repr(outp)
                dirty = False
            if pause:
                show_paused(term)

            inp = term.inkey(timeout=0.01 if not pause else None)
            if inp.lower() == 'q':
                break
            if inp == '?':
                assert False, "don't panic"
            if inp == '\x0c':
                dirty = True
            if inp in ('[', ']'):
                term.color_distance_algorithm = next_algo(
                    term.color_distance_algorithm, inp == '[')
                show_please_wait(term)
                dirty = True
            if inp == ' ':
                pause = not pause
