" A two-state horizontal lightbar for 'The Progressive' BBS. "
__author__ = "Jeffrey Quast <dingo@1984.ws>"
__contributors__ = []
__copyright__ = "Copyright (c) 2008 Jeffrey Quast"
__version__ = "$Id: leftright.py,v 1.3 2009/05/31 16:12:05 dingo Exp $"
__license__ = "ISC"

from session import getsession
from output import echo
from input import getch


class LeftRightClass:
  LEFT, RIGHT = 1, 2
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
  left_text   = ' Left '
  right_text  = ' Right '

  def __init__(self, xypos, state=None):
    """
    @param xypos: screen xy position as tuple
    @param state: starting position
    """
    self.x, self.y = xypos
    self.state = state if state is not None else self.RIGHT
    self.terminal = getsession().terminal
    self.highlight = self.terminal.reverse
    self.lowlight = self.terminal.normal

  def refresh(self, setState=-1):
    " redraw, optionaly set state (LEFT or RIGHT) "
    if setState == -1:
      state = self.state
    else:
      state = setState

    if state == self.LEFT:
      leftattr,rightattr = self.highlight,self.lowlight
    elif state == self.RIGHT:
      leftattr,rightattr = self.lowlight,self.highlight
    else:
      raise StandardError, "illegal argument, %s, must be LEFT or RIGHT" % state
    echo (self.terminal.move(self.y, self.x) \
        + self.terminal.normal \
        + leftattr + self.left_text \
        + rightattr + self.right_text \
        + self.terminal.normal)
    self.state = state

  def clear(self):
    " erase "
    echo (self.terminal.move(self.y, self.x) + self.terminal.normal \
      + ' '*(len(self.left_text)+len(self.right_text)))

  def right(self):
    " set state to right "
    if self.state != self.RIGHT:
      self.refresh(self.RIGHT)
      self.moved = True

  def left(self):
    " set state to left "
    if self.state != self.LEFT:
      self.refresh(self.LEFT)
      self.moved = True

  def isright(self):
    """
    test lightbar state for right position.
    @return: return True if state is right.
    """
    return (self.state == self.RIGHT)

  def isleft(self):
    """
    test lightbar state for left position.
    @return: return True if state is left.
    """
    return (self.state == self.LEFT)

  def flip(self):
    """
    Flip the lightbar state, changing to left when right,
    and right when left.
    """
    if self.isright():
      self.left()
    else:
      self.right()

  def run(self, key=None, timeout=None):
    """ an action method for leftright bar:
        - set key as optional user keystroke
        - set interactive when passing keystroke
        - unset interactive to retrieve user input within timeout when key is None
        - set timeout value to return None after that time elapsed
        - unset timeout to wait for user input indefinitly when not interactive
    """
    self.moved = False
    while True:
      # check for refresh
      if self.laststate != self.state:
        self.refresh ()
      self.laststate = self.state

      # read from input
      if not key:
        key = getch(timeout)
        self.lastkey = key
        if key == None:
          self.timeout = True

      # act on key
      if key in ['\t', ' ']:
        self.flip()
      elif key in ['h', self.terminal.KEY_LEFT]:
        self.left ()
      elif key in ['l', self.terminal.KEY_RIGHT]:
        self.right ()
      elif key in ['q', self.terminal.KEY_EXIT]:
        self.exit = True
      elif key in [self.terminal.KEY_ENTER, 'y', 'n']:
        # yes is on left side
        if key == 'y' or (key == self.terminal.KEY_ENTER and self.isleft()):
          self.left ()
        # and no on right
        elif key == 'n' or (key == self.terminal.KEY_ENTER and self.isright()):
          self.right ()
        return self.state # selection was made
      if self.interactive or self.exit:
        return None # no selection was made or user exit
      key = ''


class YesNoClass(LeftRightClass):
  YES, NO     = 1, 2
  " A horizontal yes/no lightbar "
  left_text   = '  Yes  '
  right_text  = '  No  '
  def __init__(self, xypos, state=None):
    """
    @param xypos: screen xy position as tuple
    @param state: state, default=YES
    """
    LeftRightClass.__init__(self, xypos,
        state if state is not None else self.YES)


class PrevNextClass(LeftRightClass):
  PREV, NEXT  = 1, 2
  " A horizontal previous/next lightbar "
  left_text  = '<- pREV  '
  right_text = ' nEXT ->'
  def __init__(self, xypos, state=None):
    """
    @param xypos: screen xy position as tuple
    @param state: state, default=NEXT
    """
    LeftRightClass.__init__(self, xypos,
        state if state is not None else self.NEXT)
