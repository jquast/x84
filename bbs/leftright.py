" A two-state horizontal lightbar for 'The Progressive' BBS. "
__author__ = "Jeffrey Quast <dingo@1984.ws>"
__contributors__ = []
__copyright__ = "Copyright (c) 2008 Jeffrey Quast"
__version__ = "$Id: leftright.py,v 1.3 2009/05/31 16:12:05 dingo Exp $"
__license__ = "ISC"

from output import echo
from input import getch
from ansi import *
import curses

LEFT, RIGHT = 1, 2

class LeftRightClass:
  """
  A two-state horizontal lightbar.

  @ivar timeout: number of seconds to poll for input.
  @ivar interactive: run() returns immediately when interactive, otherwise
    only when a selection is made.
  @ivar exit: an escape sequence made by user.
  @ivar laststate: prior state since last change, used to detect refresh.
  @ivar state: current state, set default state in init().
  @ivar lastkey: last keypress.
  @ivar x: left-most screen position.
  @ivar y: vertical screen position.
  @ivar highlight: color sequence for selected value.
  @ivar lowlight: color sequence for unselected value.
  @ivar left_text: string sequence displayed for left entry.
  @ivar right_text: string sequence displayed for right entry.
  """

  timeout     = False
  interactive = False
  exit        = False
  laststate   = -1
  lastkey     = None
  highlight   = color(INVERSE)
  lowlight    = color()
  left_text   = ' Left '
  right_text  = ' Right '

  def __init__(self, xypos, state=RIGHT):
    """
    @param xypos: screen xy position as tuple
    @param state: starting position
    """
    self.x, self.y = xypos
    self.state = state

  def refresh(s, setState=-1):
    " redraw, optionaly set state (LEFT or RIGHT) "
    if setState == -1:
      state = s.state
    else:
      state = setState

    if state == LEFT:
      leftattr,rightattr = s.highlight,s.lowlight
    elif state == RIGHT:
      leftattr,rightattr = s.lowlight,s.highlight
    else:
      raise StandardError, "illegal argument, %s, must be LEFT or RIGHT" % state
    echo (pos(s.x, s.y) + color() \
      + leftattr + s.left_text \
      + rightattr + s.right_text \
      + color())
    s.state = state

  def clear(s):
    " erase "
    echo (pos(s.x, s.y) + color() \
      + ' '*(len(s.left_text)+len(s.right_text)))

  def right(s):
    " set state to right "
    if s.state != RIGHT:
      s.refresh(RIGHT)
      s.moved = True

  def left(s):
    " set state to left "
    if s.state != LEFT:
      s.refresh(LEFT)
      s.moved = True

  def isright(s):
    """
    test lightbar state for right position.
    @return: return True if state is right.
    """
    return (s.state == RIGHT)

  def isleft(s):
    """
    test lightbar state for left position.
    @return: return True if state is left.
    """
    return (s.state == LEFT)

  def flip(s):
    """
    Flip the lightbar state, changing to left when right,
    and right when left.
    """
    if s.isright():
      s.left()
    else:
      s.right()

  def run(s, key=None, timeout=None):
    """ an action method for leftright bar:
        - set key as optional user keystroke
        - set interactive when passing keystroke
        - unset interactive to retrieve user input within timeout when key is None
        - set timeout value to return None after that time elapsed
        - unset timeout to wait for user input indefinitly when not interactive
    """
    s.moved = False
    while True:
      # check for refresh
      if s.laststate != s.state:
        s.refresh ()
      s.laststate = s.state

      # read from input
      if not key:
        key = getch(timeout)
        s.lastkey = key
        if key == None:
          s.timeout = True

      # act on key
      if key in ['\t', ' ']:
        s.flip()
      elif key in ['h', curses.KEY_LEFT]:
        s.left ()
      elif key in ['l', curses.KEY_RIGHT]:
        s.right ()
      elif key in ['q', curses.KEY_EXIT]:
        s.exit = True
      elif key in [curses.KEY_ENTER, 'y', 'n']:
        # yes is on left side
        if key == 'y' or (key == curses.KEY_ENTER and s.isleft()):
          s.left ()
        # and no on right
        elif key == 'n' or (key == curses.KEY_ENTER and s.isright()):
          s.right ()
        return s.state # selection was made
      if s.interactive or s.exit:
        return None # no selection was made or user exit
      key = ''

YES, NO     = 1, 2

class YesNoClass(LeftRightClass):
  " A horizontal yes/no lightbar "
  left_text   = '  Yes  '
  right_text  = '  No  '
  def __init__(self, xypos, state=YES):
    """
    @param xypos: screen xy position as tuple
    @param state: state, default=YES
    """
    LeftRightClass.__init__(self, xypos, state)

PREV, NEXT  = 1, 2

class PrevNextClass(LeftRightClass):
  " A horizontal previous/next lightbar "
  left_text  = '<- pREV  '
  right_text = ' nEXT ->'
  def __init__(self, xypos, state=NEXT):
    """
    @param xypos: screen xy position as tuple
    @param state: state, default=NEXT
    """
    LeftRightClass.__init__(self, xypos, state)
