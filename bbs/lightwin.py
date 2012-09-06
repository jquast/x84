"""
Lightbar user interface for X/84, http://1984.ws
$Id: lightwin.py,v 1.5 2010/01/06 19:45:51 dingo Exp $
"""

__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2006, 2007, 2008, 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

from output import echo
from input import getch
import ansiwin
import ansi
import curses
import log

class LightClass (ansiwin.InteractiveAnsiWindow):
  KMAP = { \
    'home':  ['y', curses.KEY_HOME],
    'end':   ['n', curses.KEY_END],
    'pgup':  ['h', curses.KEY_PPAGE],
    'pgdown':['l', curses.KEY_NPAGE],
    'up':    ['k', curses.KEY_UP],
    'down':  ['j', curses.KEY_DOWN],
    'quit':  ['q', curses.KEY_EXIT] \
  }

  alignment='left'

  # user postion in the list
  item, shift = 0, 0

  # oitem and ishift are used as dirty flags
  oitem, oshift = -1, -1
  bottom = 0
  selection = 0

  # selection is the numeric position in list, not its' contents
  byindex = False

  # behavior
  moved = True

  def __init__(self, h, w, y, x, xpad=0, ypad=0):
    ansiwin.InteractiveAnsiWindow.__init__ (self, h, w, y, x)

    self.content = []
    self.lastkey = ' '
    self.xpad, self.ypad = xpad, ypad

    # Drawing
    self.visibleWidth, self.visibleHeight = self.w -(self.xpad*2), self.h -(self.ypad*2) # margins

  def adjshift(self, value):
    """ adjust top visible row in list
    """
    if self.shift != value:
      self.oshift = self.shift
      if self.debug: log.write ('lightstep', 'adjshift %i->%i' % (self.shift, value))
      self.shift = value
      self.moved = True

  def adjitem(self, value):
    """ adjust visible item in list
    """
    if self.item != value:
      self.oitem = self.item
      if self.debug: log.write ('lightstep', 'adjsitem %i->%i' % (self.item, value))
      self.item = value
      self.moved = True

  def setselection(self):
    # set selection to index
    self.index = self.shift +self.item
    if not self.content:
      if self.debug: log.write ('lightstep', 'empty list in setselection()')
      return
    if self.byindex:
      self.selection = self.index
    else:
      self.selection = self.content[self.index]

  def add (self, string, refresh=True):
    self.content.append (string)
    self.update (self.content, refresh)

  def resize(self, h=-1, w=-1, y=-1, x=-1, refresh=True):
    " Adjust visible bottom "
    ansiwin.InteractiveAnsiWindow.resize (self, h, w, y, x)
    # Drawing
    self.visibleWidth, self.visibleHeight = self.w-2, self.h-1 # margins

    if refresh:
      # recalculate selection
      self.update (self.content, True)

  def display_entry(self, ypos, entry, highlight=False):
    """ display entry at ypos, high or unhighlighted
    """
    echo (self.pos(self.xpad, self.ypad +ypos))
    if highlight:
      echo (self.colors['highlight'])
    else:
      echo (self.colors['lowlight'])
    self.oitem, self.oshift = self.item, self.oshift
    if entry >= len(self.content):
      raise ValueError, "entry out of bounds in display_entry. entry=%s len(list)=%s" % (entry, len(self.content))
    def align(s, n):
      if self.alignment == 'left':
        return s.ljust(n)
      elif self.alignment == 'right':
        return s.rjust(n)
      elif self.alignment == 'center':
        return s.center(n)
      assert 0, 'invalid alignment: %(alignment)s' % self
    echo (align(self.content[entry], self.visibleWidth))
    echo (ansi.color())

  def refresh (self):
    """ display all viewable items in lightbar object.
        loop entry as range(visible top to visible bottom)
        set ypos as entry minus window shift
        display entry at visible row ypos
    """
    if self.debug: log.write ('lightstep', 'refresh idx: %s' % (repr(range(self.shift, self.bottom +self.shift))))
    for n, entry in enumerate(range(self.shift, self.bottom +self.shift)):
      ypos = entry -self.shift
      if ypos == self.item:
        self.display_entry(ypos, entry, highlight=True)
      else:
        self.display_entry(ypos, entry)

    # clear remaining lines in window
    y = self.bottom
    while y < self.visibleHeight:
      echo (self.pos(self.xpad, self.ypad+y) + self.glyphs['fill']*(self.visibleWidth))
      y += 1
    self.oshift = self.shift

  def update(self, list, refresh=True):
    """ Update list data, list, adjust selection position, self.item and self.shift,
        and review bottom-most printable row index, self.bottom.
    """
    self.content, self.items = list, len(list)
    if not self.items:
      self.content = ['']
    self.position (self.item, self.shift)
    self.set_bottom ()
    if refresh:
      self.refresh ()

  def set_bottom(self):
    """ find visible self.bottom of list
    """
    obottom = self.bottom
    if self.shift +(self.visibleHeight -1) > self.items:
      # items fit within displayable window, set bottom to last item
      self.bottom = self.items
    else:
      # items fit beyond window, set bottom to printable height
      self.bottom = self.visibleHeight
    if obottom != self.bottom and self.debug:
      if self.debug: log.write ('lightstep',  'bottom %s -> %s' % (obottom, self.bottom))

  def position(self, item, shift=0):
    """ Move to specific position in window, item being the visible row
        starting at 0 on top down to the bottom most visible position in
        our viewing window. Shift being the number of rows shifted from
        the top-post item to show this viewable slice.
        If target item and shift position cannot be met exactly, first
        boundschecking will truncate to ensure data selection is within range,
        then window will be shifted to ensure the window is as full as possible,
        while still retaining the desired y position
    """
    self.adjitem (item)
    self.adjshift (shift)

    # if selected item is out of range of
    # new list, then move selection to end
    # of current list
    if self.shift and self.shift + self.item +1 > self.items:
      if self.debug: log.write ('lightstepclass', 'pos-item out of range')
      self.adjshift (self.items -self.visibleHeight +1)
      self.adjitem (self.visibleHeight -2)

    # if we are a shifted window, scroll up, while
    # holding to our selection position,
    # until bottom-most item is within visable range
    while self.shift and self.shift + self.visibleHeight -1 > self.items:
      if self.debug: log.dbeug ('lightstepclass', 'pos-scroll up')
      self.adjshift (shift -1)
      self.adjitem (self.item +1)

    # when a window is not shiftable, ensure
    # selection is less than total (truncate to last item)
    # This loop occurs, for instance, if we are selecting the last item,
    # and the list is truncated to a smaller length. We want to ensure
    # the selection is on a valid item!
    while self.item and self.item +self.shift >= self.items:
      self.adjitem (self.item -1)
    self.setselection()

  def down(self):
    """ move down one entry
    """
    if self.item +self.shift +1 < self.items:
      if self.debug: log.write ('lightstep', 'down-ok')
      if self.item+1 < self.bottom:
        if self.debug: log.write ('lightstep', 'down-move')
        self.adjitem (self.item +1)
      elif self.item < self.items:
        if self.debug: log.write ('lightstep', 'down-scroll')
        self.adjshift (self.shift +1)
    else:
      if self.debug: log.write ('lightstep', 'down-no')

  def up(self):
    """ move up one entry
    """
    if self.item +self.shift >= 0:
      if self.debug: log.write ('lightstep', 'up-ok')
      if self.item >= 1:
        if self.debug: log.write ('lightstep', 'up-move')
        self.adjitem (self.item -1)
      elif self.shift > 0:
        if self.debug: log.write ('lightstep', 'up-scroll')
        self.adjshift (self.shift -1)
    else:
      if self.debug: log.write ('lightstep', 'up-no')

  def pagedown(self):
    """ move down one page
    """
    if self.items < self.visibleHeight:
      self.adjitem (self.items-1)
    elif self.shift +self.visibleHeight < self.items -self.visibleHeight:
      self.adjshift (self.shift +self.visibleHeight)
    else:
      if self.shift != self.items -self.visibleHeight:
        # shift window to last page
        self.adjshift (self.items -self.visibleHeight)
      else:
        # already at last page, goto end
        self.end()

  def pageup(self):
    """ move up one page
    """
    if self.items < self.visibleHeight-1:
      self.adjitem (0)
    if self.shift -self.visibleHeight > 0:
      self.adjshift (self.shift -self.visibleHeight)
    else:
      # shift window to first page
      if self.shift != 0:
        self.adjshift (0)
      # already at first, goto home
      else: self.home ()

  def home(self):
    """ move to first entry
    """
    if self.item != 0 or self.shift != 0:
      self.adjitem (0)
      self.adjshift (0)

  def end(self):
    """ move to last entry
    """
    if self.items < self.visibleHeight:
      self.adjitem (self.items -1)
    else:
      self.adjshift (self.items -self.visibleHeight)
      self.adjitem (self.visibleHeight -1)

  def process_keystroke(self, key):
    """ Process the keystroke received by run method and take action.
    """
    if key in self.KMAP['home']: self.home ()
    elif key in self.KMAP['end']: self.end ()
    elif key in self.KMAP['pgup']: self.pageup ()
    elif key in self.KMAP['pgdown']: self.pagedown ()
    elif key in self.KMAP['up']: self.up ()
    elif key in self.KMAP['down']: self.down ()
    elif key in self.KMAP['quit']: self.exit = True

  def run (self, key=None, timeout=None):
    self.lastkey = None
    self.moved = False
    self.timeout = False
    self.exit = False

    def chkrefresh ():
      if self.oshift != self.shift and self.oshift != -1:
        if self.debug: log.write ('lightstep', 'oshift: %s, shift: %s' % (self.oshift, self.shift))
        # page shift, refresh entire page
        self.refresh ()
      elif self.moved:
        if self.oitem != -1:
          # unlight old entry
          self.display_entry (self.oitem, self.oitem +self.shift)
        # highlight new entry
        self.display_entry (self.item, self.item +self.shift, highlight=True)

    while True:
      # check for and refresh before reading key
      chkrefresh ()
      if not key or not self.interactive:
        key = getch(timeout)
        if key == None:
          self.timeout = True
        else:
          self.process_keystroke (key)
      else:
        self.process_keystroke (key)
      self.lastkey = key

      self.setselection()
      # returns
      if key in [curses.KEY_ENTER]:
        return self.selection
      elif self.exit:
        return False
      if self.interactive:
        # check for and refresh before return
        chkrefresh ()
        break
      key = ''
    return None
