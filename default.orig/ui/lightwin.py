"""
lightbar class for 'The Progressive' BBS.
Copyright (c) 2006, 2007 Jeffrey Quast <jeffrey.quast@gmail.com>
$Id: lightwin.py,v 1.12 2009/05/17 21:02:35 dingo Exp $

LightClass is a lightbar display class for displaying printable data sets
in a tabular format with movement and interaction. Recieves as input to
.update() a list of strings, and as output will refresh during update, or
directly with .refresh(), and as apropriate during movement in method .run().

Lightclass recieves input through the update() function a list of stringself.

The mid-level method .pos() accepts as input the item and shift number
of a selection. Variable shift is the number of non-visible records from
the top of the data set to the top of the viewable window. Variable item
is the number of records from the top of the viewable window. These positions
may be saved using obj.shift and obj.item and recalled into .pos(). The
window height may be adjusted using .resize(h=newheight), for instance.

By default, the high-level .run() method acts as the entry point to a
lightbar menu. Last keypress may be retrieved using variable obj.lastkey
after return and set as None when no keypress occurs within timeout. When
interactive is set to True, .run() acts as an iterated step of a larger
loop. In this mode, movement and actions must be passed as variable key,
defined by the controlling loop.

The string in the position of the current selection in the dataset is
returned. When byindex is set to True, the position of the current
selection in the list is returned.

object creation requires as the argument an object created
from the ansi windowing class, L{ansiwin}.

The lightstepclass is a stacked list of lightbars, allowing you
to traverse left or right. This behavios similar to the nextstep
file browser (also seen in OSX). When traversing right, suitable
data is returned by the .retrieve() method by passing the current
selection as the key value.

By default, .retrieve returns Null. You *must* derive this class
and overload the retrieve() method to return suitable data! An example
of this can be found in the fb.py filebrowser demonstration.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = 'Copyright (c) 2006, 2007, 2008, 2009 Jeffrey Quast'
__license__ = 'ISC'

# hard imports, anything dervied here
# must have system restarted when changed
from bbs import echo, readkey
from ansi import color, pos, attr
from ansiwin import InteractiveAnsiWindow
import log

# soft imports, anything derived from
# these may be changed
deps= ['strutils', 'keys', 'ansi']

class LightClass (InteractiveAnsiWindow):
  def __init__(self, h, w, y, x):
    InteractiveAnsiWindow.__init__ (self, h, w, y, x)

    self.list = []
    self.lastkey = ' '
    self.debug = True

    # Drawing
    self.drawWidth, self.drawHeight = self.w-2, self.h-1 # margins
    self.alignment='left'

    # user postion in the list
    self.item, self.shift   =  0,  0
    self.oitem, self.oshift = -1, -1
    self.bottom    = 0
    self.selection = 0

    # run behavior
    self.byindex     = False

    # behavior
    self.moved = True

  def adjshift(self, value):
    if self.shift != value:
      self.oshift = self.shift
      if self.debug:
        log.debug ('adjshift %i->%i' % (self.shift, value))
      self.shift = value
      self.moved = True

  def adjitem(self, value):
    if self.item != value:
      self.oitem = self.item
      if self.debug:
        log.debug ('adjsitem %i->%i' % (self.item, value))
      self.item = value
      self.moved = True

  def setselection(self):
    # set selection to index
    self.index = self.shift +self.item
    if not self.list:
      if self.debug: print 'empty list in setselection()'
      return
    if self.byindex:
      self.selection = self.index
    else:
      self.selection = self.list[self.index]

  def dumpvalues(self):
    print ' item:' + str(self.item) + ' shift:' + str(self.shift)
    print ' bottom:' + str(self.bottom) + ' items:' + str(self.items)

  def add (self, string, refresh=True):
    self.list.append (string)
    self.update (self.list, refresh)

  def resize(self, h=-1, w=-1, y=-1, x=-1, refresh=True):
    " Adjust visible bottom "
    InteractiveAnsiWindow.resize (self, h, w, y, x)

    if refresh:
      # recalculate selection
      self.update (self.list, refresh)

  def lowlight(self):
    echo (self.pos(1, self.item+1))
    echo (self.colors['ghostlight'])
    if self.item +self.shift:
      echo (strpadd (self.list[self.item +self.shift],
                     paddlen=self.drawWidth,
                     align=self.alignment))
    InteractiveAnsiWindow.lowlight(self)

  def highlight(self):
    # pass up
    InteractiveAnsiWindow.highlight (self)
    echo (self.pos(1, self.item+1))
    echo (self.colors['highlight'])
    echo (strpadd (self.list[self.item +self.shift],
                   paddlen=self.drawWidth,
                   align=self.alignment))

  def display_entry(self, ypos, entry, highlight=False):
    " display entry at ypos, high or unhighlighted"
    echo (self.pos(1, ypos))
    if highlight:
      echo (self.colors['highlight'])
    else:
      echo (self.colors['lowlight'])
    self.oitem, self.oshift = self.item, self.oshift
    if entry >= len(self.list):
      raise ValueError, "entry out of bounds in display_entry. entry= len(list)=" % (entry, len(self.list))
    echo (strpadd(self.list[entry], paddlen=self.drawWidth, align=self.alignment))
    if highlight:
      echo (color())

  def refresh (self):
    """ display all viewable items in lightbar object.
        loop entry as range(visible top to visible bottom)
        set ypos as entry minus window shift
        display entry at visible row ypos
    """
    if self.debug:
      log.debug ('refresh idx: %s' % (repr(range(self.shift, self.bottom +self.shift))))
    for n, entry in enumerate(range(self.shift, self.bottom +self.shift)):
      ypos = 1 +entry -self.shift
      try:
        if ypos == self.item+1:
          self.display_entry(ypos, entry, highlight=True)
        else:
          self.display_entry(ypos, entry)
#IF 0
      except IndexError:
        print 'IndexError on refresh: entry:' + str(entry) + ' shift:' + str(self.shift) + \
          ' bottom:' + str(self.bottom) + ' height:' + str(self.drawHeight) + \
          ' ypos:' + str(ypos)
#ENDIF

    # clear remaining lines in window
    y = self.bottom
    while y < self.drawHeight-1:
      echo (self.pos(1, 1 +y -self.shift) + ' '*(self.drawWidth))
      y += 1
    self.oshift = self.shift

  def update(self, list, refresh=True):
    """ Update list data, list, adjust selection position, self.item and self.shift,
        and review bottom-most printable row index, self.bottom.
    """
    self.list, self.items = list, len(list)
    if not self.items:
      self.list = ['']
    self.position (self.item, self.shift)
    self.set_bottom ()
    if refresh:
      self.refresh ()

  def set_bottom(self):
    " find visible self.bottom of list "
    obottom = self.bottom
    if self.shift +(self.drawHeight -1) > self.items:
      # items fit within displayable window, set bottom to last item
      self.bottom = self.items
    else:
      # items fit beyond window, set bottom to printable height
      self.bottom = self.drawHeight -1
    if obottom != self.bottom and self.debug:
      print 'bottom', obottom, '->', self.bottom

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
      if self.debug: print 'pos-item out of range'
      self.adjshift (self.items -self.drawHeight +1)
      self.adjitem (self.drawHeight -2)

    # if we are a shifted window, scroll up, while
    # holding to our selection position,
    # until bottom-most item is within visable range
    while self.shift and self.shift + self.drawHeight -1 > self.items:
      if self.debug: print 'pos-scroll up'
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
    " move down one entry"
    if self.item +self.shift +1 < self.items:
      if self.debug: print 'down-ok'
      if self.item+1 < self.bottom:
        if self.debug: print 'down-move'
        self.adjitem (self.item +1)
      elif self.item < self.items:
        if self.debug: print 'down-scroll'
        self.adjshift (self.shift +1)
    else:
      if self.debug: print 'down-no'

  def up(self):
    " move up one entry"
    if self.item +self.shift >= 0:
      if self.debug: print 'up-ok'
      if self.item >= 1:
        if self.debug: print 'up-move'
        self.adjitem (self.item -1)
      elif self.shift > 0:
        if self.debug: print 'up-scroll'
        self.adjshift (self.shift -1)
    else:
      if self.debug: print 'up-no'

  def pagedown(self):
    " move down one page"
    if self.items < self.drawHeight-1:
      self.adjitem (self.items-1)
    elif self.shift +self.drawHeight < self.items -self.drawHeight:
      self.adjshift (self.shift +self.drawHeight)
    else:
      if self.shift != self.items -self.drawHeight +1:
        # shift window to last page
        self.adjshift (self.items -self.drawHeight +1)
      else:
        # already at last page, goto end
        self.end()

  def pageup(self):
    " move up one page"
    if self.items < self.drawHeight-1:
      self.adjitem (0)
    if self.shift -self.drawHeight > 0:
      self.adjshift (self.shift -self.drawHeight)
    else:
      # shift window to first page
      if self.shift != 0:
        self.adjshift (0)
      # already at first, goto home
      else: self.home ()

  def home(self):
    " move to first entry"
    if self.item != 0 or self.shift != 0:
      self.adjitem (0)
      self.adjshift (0)

  def end(self):
    " move to last entry"
    if self.items < self.drawHeight-1:
      self.adjitem (self.items -1)
    else:
      self.adjshift (self.items -self.drawHeight +1)
      self.adjitem (self.drawHeight -2)

  def run (self, key=None, timeout=None):
    """ an action method for lightbar window:
        - set key as optional user keystroke
        - set timeout value to return None after that time elapsed
        - unset timeout to wait for user input indefinitly when not interactive
    """
    self.timeout, self.exit = False, False

    while True:
      if self.oshift != self.shift and self.oshift != -1:
        if self.debug: print 'oshift', self.oshift, 'shift', self.shift
        # page shift, refresh entire page
        self.refresh ()
      elif self.moved:
        if self.oitem != -1:
          # unlight old entry
          self.display_entry (self.oitem+1, self.oitem +self.shift)
        # highlight new entry
        self.display_entry (self.item+1, self.item +self.shift, highlight=True)
        self.moved = False

      if not key or not self.interactive:
        key = readkey(timeout)
        self.lastkey = key
        if key == None:
          self.timeout = True
      if   key in ['y', KEY.HOME]: self.home ()
      elif key in ['u', KEY.PGUP]: self.pageup ()
      elif key in ['j', KEY.DOWN]: self.down ()
      elif key in ['k', KEY.UP]: self.up ()
      elif key in ['b', KEY.END]: self.end ()
      elif key in ['n', KEY.PGDOWN]: self.pagedown ()
      elif key in ['q', KEY.ESCAPE, '\030']: self.exit = True

#IF 0
      elif key == '\001': # debug
        echo(self.pos(1,1) + ' item:' +str(self.item) +' shift:' +str(self.shift))
        echo(self.pos(1,2) + ' bottom:' +str(self.bottom) +' items:' +str(self.items))
        readkey()
      elif key and self.debug:
        print 'LightClass: throwing out ' + repr(key)
#ENDIF

      self.setselection()

      # returns
      if key in [KEY.ENTER]:
        return self.selection
      elif self.exit:
        return False
      if self.interactive:
        break
      key = ''
    return None

class LightStepClass (InteractiveAnsiWindow):
  """ A general nextstep-like traversing clasself. Mainage an array
      of LightClass instances by walking left and right through
      nodes of a linear dataset. Override function retrieve(key),
      and call left() and right() to walk.
  """
  # set of lightbar objects, 0 is trunk
  lightset = []

  # Index of active window, -1 create root on first right()
  depth = -1

  # set debug level to 2 for child lightbar objects to also set debug on insert
  debug = False

  drawWidth = 0

  def __init__(self, h, w, y, x):
    InteractiveAnsiWindow.__init__ (self, h, w, y, x)
    self.drawWidth = self.w-2

  def isinview(self, lightrec=None):
    """ return True if target lightrec window is within LightStepClass window,
        set lightrec to target lightrec obj, otherwise self.active() """
    if not lightrec:
      lightrec = self.active()
    return self.willfit(lightrec)

  def retrieve(self, key):
    """ Override this function to return data suitable for a lightbar,
        lookup using unique varable key. This could be a key of a
        dictionary, index of a list, a filepath, a username, etc.

        This class will -not- work unless you override this function!

        See example in script/fb.py for a filebrowser class, or
        script/ue.py for a user editor class
        """
    return []

  def getContentWidth(self, data):
    " Return largest window size necessary to display data. "
    return maxwidth(data, self.w)+2

  def active(self):
    " Return active window. "
    lb = self.lightset[self.depth]
    lb.pos (lb.item, lb.shift)
    return lb

  def activate(self, pos, key=None):
    " Make window at pos active and highlight border. "
    active = self.lightset[pos]
    active.interactive = True
    if key:
      active.update(self.retrieve(key))
      active.oshift, active.oitem = -1, -1
    self.refresh ()
    active.refresh()
    active.highlight()
    return self.active()

  def dragScreen(self, direction='right'):
    """ shift all windows horizontally in direction specified,
        until the active window is visable within our viewport.
        by value is number of columns to shift by
    """
    if direction == 'right':
      by=1
    elif direction == 'left':
      by=-1
    else:
      raise ValueError, "Expected 'left' or 'right', recieved:%s" % (repr(direction))

    if not self.isinview():
      while not self.isinview():
        i=0
        for n in range(0, len(self.lightset)):
          lr = self.lightset[n]
          lr.x += by
          i += 1
    if not self.lightset[0].isinview():
      while self.isinview():
        i=0
        for n in range(0, len(self.lightset)):
          lr = self.lightset[n]
          lr.x += by
          i += 1
      lr.x -= by

#  def leftmostOutOfView(self, start=0, end=-1):
#    "return first far-left window out of view, starting at start="
#    if end == -1:
#      end = len(self.lightset)
#    for n in range(start, end):
#      if not self.isinview(self.lightset[n]):
#        return n
#
#  def leftmostInView(self, start=0, end=-1):
#    " return first far-left window in view"
#    if end == -1:
#      end = len(self.lightset)
#    for n in range(start, end):
#      if self.isinview(self.lightset[n]):
#        return n
#
#  def cleanRightOf(self, lightrec):
#      " return sequence that cleans area rightof the leftmost edge of specified lightrec. "
#      seq = color()
#      x = lightrec.x
#      width = self.x +self.w -x
#      for y in range(lightrec.y, lightrec.y +lightrec.h):
#        print 'xy#'+str(x)+','+str(y),
#        seq += pos(x, y) + self.glyphs['erase']*width
#      print
#      return seq
#
#  def cleanLeftOf(self, lightrec):
#      " return sequence that cleans area leftof the leftmost edge of specified lightrec. "
#      seq = color()
#      x = self.x
#      width = lightrec.x
#      for y in range(lightrec.y, lightrec.y +lightrec.h):
#        print 'xy:'+str(x)+','+str(y),
#        seq += pos(x, y) + self.glyphs['erase']*width
#      print
#      return seq

  def left(self, key=None):
    """
       Move left in the lightbar stack. If the data returning to needs to be
       refreshed, pass key to re-populate. If we cannot traverse left (root node),
       False is returned.
    """
    if not self.depth:
      return False

    self.active().lowlight()
    self.remove (self.depth)
    self.depth -=1

    self.dragScreen ('right')

    return self.activate(self.depth, key)

  def right(self, key):
    """
        Move right in the lightbar stack, using key to value contents from
        the retrieve() method. If no data is retrieved by key, False
        is returned (deny traverse)
    """
    data = self.retrieve(key)
    if not data:
      return False

    self.depth +=1
    self.insert (self.depth, data)

    # shift screen if necessary
    if not self.isinview():
      self.dragScreen ('left')

    return self.activate(self.depth)

  def nextx(self):
    " Return xpos of right-most edge of lowest record. "
    x = self.lightset[0].x
    for n in range(0, len(self.lightset)):
      x += self.lightset[n].w
    return x

  def remove(self, level):
    " Erase all lightobjects at position level and above"
    for n in range(level, len(self.lightset)):
      if self.isinview(self.lightset[n]):
        self.lightset[n].clean ()
      else:
        continue
    self.lightset = self.lightset[:level]

  def refresh (self, start=0, end=-1):
    " Refresh all lightbar windows from start to end "
    self.clean ()
    if end == -1:
      end = len(self.lightset)
    for n in range(start, end):
      lightrec = self.lightset[n]
      if not self.isinview(lightrec):
        continue
      if n == self.depth:
        lightrec.highlight ()
        None
      else:
        lightrec.lowlight ()
      lightrec.refresh ()

  def insert(self, p, data):
    " Insert lightobj at position p in self.lightset. "
    if not len(self.lightset) or self.depth == 0:
      if self.debug: print 'create root tree', self.depth
      self.lightset = [LightClass(self.h, self.getContentWidth(data), self.y, self.x)]
      self.lightset[p].update (data)
      self.lightset[p].interactive = True
      return

    elif p< len(self.lightset):
      if self.debug:
        log.debug ('removing %i windows before append, rightof %i' % (len(self.lightset) -1 -p, p))
      self.remove (p)

    if self.debug:
      log.debug ('append new window #%i, p=%i (x=%i)' % (len(self.lightset)-1, p, self.nextx()))

    self.lightset.append \
      (LightClass(self.h, self.getContentWidth(data), self.y, self.nextx()))

    if self.debug > 1:
      self.lightset[p].debug = True
    # lightsets are always interactive
    self.lightset[p].interactive = True
    self.lightset[p].update (data, refresh=False)

lightclass = LightClass # XXX depricated
lightstepclass = LightStepClass # XXX depricated
