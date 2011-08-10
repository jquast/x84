__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']

class Particle():
  xforce, yforce = 0, .3 # naturalyl fall down
  x,y = 0.0,0.0 # cur pos
  xl,yl= 0.0,0.0 # last pos
  active = True
  destroy = False
  dirty = False
  def __init__(self, x, y, xforce=None, yforce=None):
    self.x, self.y = x,y
    if xforce != None: self.xforce = xforce
    if yforce != None: self.yforce = yforce

  def draw(self):
    if self.active:
      echo (pos(int(self.x),int(self.y)) + 'o')
    self.dirty = False

  def erase(self):
    print 'erase', int(self.xl), int(self.yl), int(self.x), int(self.y)
    echo (pos(int(self.xl),int(self.yl)) + '.')

  def next(self):
    # apply force,
    if self.xforce != 0.0:
      self.x += self.xforce
      if int(self.x) != int(self.xl):
        print self.x, self.xl, 'dirty'
        self.dirty=True
    if self.yforce != 0.0:
      self.y += self.yforce
      if int(self.y) != int(self.yl):
        print self.y, self.yl, 'dirty'
        self.dirty = True
    # check for dead movement
    if self.active and self.x == self.xl \
    and self.y == self.yl and not self.xforce \
    and not self.yforce:
      # this particle is no longer moving or has
      # no intention of moving, it is inactive
      self.active = False
      print 'p died@', p.x, p.y
    self.xl = 0.0+self.x
    self.yl = 0.0+self.y

class Cell():
  x,y = 0.0,0.0 # cell position
  density = 0.0 # density mask... up to FULL_CELL
  FULL_CELL = 10 # mm ya
  X_REBOUND = 0.3
  Y_REBOUND = 0.2
  X_RESISTANCE = 0.1
  Y_GRAVITY = 0.25
  Y_WASHFACTOR = 2 # whatevr
  X_WASHFACTOR = 1 # yeah, ok

  def __init__(self, x, y):
    self.x, self.y = x,y

  def calc_region(self, particles, z):
    print 'calc region', 'np=',len(particles), 'z=',z
    # z describes a 9-value array of density dimensions around (x,y)*
    #   012
    #   3*5
    #   678
    for p in particles:
      # coerce each particle to 'center' of this cell, that is
      # prevent it from travelling indefiniteyl horizontal
      # and use max and min to prevent jiggle
      if p.xforce > 0.0:
        # particle is moving right, resist left
        p.xforce = max([p.xforce-self.X_RESISTANCE, 0.0])
      else: # p.xforce < 0.0
        # moving left, resist right
        p.xforce = min([p.xforce+self.X_RESISTANCE, 0.0])
      if p.yforce < 0.0:
        # moving upwards, apply downward gravity
        p.yforce += self.Y_GRAVITY
      elif p.yforce < (self.Y_GRAVITY * self.Y_WASHFACTOR):
        # moving downwards, apply gravity,
        p.yforce += self.Y_GRAVITY # XXX but no faster than factor of Y_WASHFACTOR?

      # if under-regions are full or too dense
      if min([z[6],z[7],z[8]]) >= self.FULL_CELL:
        # and we have any significant downforce,
        if p.yforce >= self.Y_GRAVITY/self.Y_WASHFACTOR:
          # reverse that force verticalyl as a factor of gravity to washfactor,
          # (like thick milk)
          p.yforce *= (self.Y_WASHFACTOR * self.Y_GRAVITY) * -1
        elif p.yforce > 0.0:
          # too soft, stop it in its tracks (jiggle prevention)
          p.yforce = 0.0
        # else:
          # gravity already applied, continue on upwards

      # under regions are not full,
      else:
        p.yforce += self.Y_GRAVITY # fall down,
        # no horizontal movement,
        if p.xforce == 0.0:
          # the cell below us is of highest density of nearest cells,
          if z[7] > min([z[6],z[8]]):
            # in the case of a nearby cell being lower,
            if z[6] != z[8]:
              # fall left or right, towards lowest cell
              p.xforce = self.X_REBOUND if z[8] < z[6] else self.X_REBOUND -1
            # in the case of having no preferece,
            else:
              # fall a random direction
              p.xforce = random.choice([self.X_REBOUND,self.X_REBOUND *-1])
              # make target cell 'denser'
              if p.xforce > 0.0:
                    z[8] +=1
              else: z[6] += 1
          else:
            # fall straight downards
            z[7] += 1
        # moving left or right, but target cell is denser
        elif (p.xforce < 0.0 and sum([z[3],z[6]]) > sum([z[4],z[7]])) \
        or (p.xforce > 0.0 and sum([z[2],z[8]]) > sum([z[4],z[7]])):
          # gravitate upwards, no more than factor of Y_WASHFACTOR
          p.yforce = max([self.Y_REBOUND *-(self.Y_WASHFACTOR), p.yforce-self.Y_REBOUND])
          if p.xforce < 0.0:
                z[0] += 1
          else: z[2] += 1
        #else:
          # lowest cell is thinnest, otherwise increase horizontal travel speed, as adjacent, but
          # lower cell is even thinner
          #if p.xforce < 0.0:
          #  #p.xforce -= self.X_REBOUND
          #  z[3] += 1
          #else:
          #  #p.xforce += self.X_REBOUND
          #  z[5] += 1
          #   012
          #   3*5
          #   678


class Playground():
  particles = [] # scattered list
  cells = {} # keyed by (row,col)
  pps = 0 # particles per second
  width = 0
  height = 0
  pystarts = [] # random (x,y) locations for particle starts,
  pxstarts = [] # causes an implied random symmetry
  pxforces = [] # same for (x,y) directional force,
  pyforces = [] # again, implied symmetry
  last_t = 0 # time when particles were last created
  def __init__(self, width, height, pystarts, pxstarts, \
               pxforces, pyforces, pps=1):
    # XXX
    # accept a solid 'rock' mask (density = CELL_FULL)
    self.width, self.height = width, height
    self.pps = pps# number of new particles per second
    self.pxstarts, self.pystarts = pxstarts, pystarts
    self.pxforces, self.pyforces = pxforces, pyforces

    # create cell grid for density mask
    self.init_grid()
    # toss particles on init
    self.inflow()

  def init_grid(self):
    # init cells as 2d grid of Cell() instances,
    for row in range(self.height):
      for col in range(self.width):
        self.cells[(row,col)] = Cell(row,col)
    # with a rock bottom... ??
    for col in range(self.width):
      xy = (self.height-1,col)
      self.cells[xy].density = 999

  def inflow(self):
    # create onyl up to n particles per second that has elapsed,
    elapsed = timenow() - self.last_t
    print elapsed, 1.0/self.pps
    if elapsed > 1.0/self.pps:
      # in the case that more than a second has elapsed,
      # or on init, do not create any more than total pps
      for n in range(min([self.pps,elapsed*self.pps])):
        self.particles.append (Particle \
          (x=random.choice(self.pxstarts), y=random.choice(self.pystarts),
           xforce=random.choice(self.pxforces), yforce=random.choice(self.pyforces)))
        self.last_t = timenow()

  def next(self,width=None, height=None):
    # purpose here is to iterate row by row, column by column,
    # and within our columular loop, reference each particle onyl once!
    # a still image; the calc_region makes temporary adjustments to its
    # dynamic map localyl to consider multiple particles per cell conflicts

    self.inflow ()

    # first, create an ordered list of rows and their active particles,
    rows = dict([ (row,[p for p in self.particles \
      if p.active and int(p.y)==row]) \
        for row in range(self.height)])

    for row, particles in rows.items():
      cols = uniq([int(p.x) for p in particles])
      for col in [c for c in cols if c > 1 and c < self.width-1]:
        cell = self.cells[(row,col)]
        if row >= self.height-1:
          for p in particles: p.active = False
          continue
        # create 3x3 density map surrounding active particle
        z0d = self.cells[(row-1,col-1)].density
        z1d = self.cells[(row-1,col)].density
        z2d = self.cells[(row-1,col+1)].density
        z3d = self.cells[(row,col-1)].density
        z4d = self.cells[(row,col)].density
        z5d = self.cells[(row,col+1)].density
        z6d = self.cells[(row+1,col-1)].density
        z7d = self.cells[(row+1,col)].density
        z8d = self.cells[(row+1,col+1)].density
        # and add it to number of particles @ cell pos for relative density
        z0 = len([p for p in rows[row-1] if int(p.x) == col-1])+z0d \
           if rows.has_key(row-1) else z0d
        z1 = len([p for p in rows[row-1] if int(p.x) == col])+z1d \
           if rows.has_key(row-1) else z1d
        z2 = len([p for p in rows[row-1] if int(p.x) == col+1])+z2d \
           if rows.has_key(row-1) else z2d
        z3 = len([p for p in rows[row] if int(p.x) == col-1])+z3d
        z4 = len([p for p in rows[row] if int(p.x) == col])+z4d
        z5 = len([p for p in rows[row] if int(p.x) == col+1])+z5d
        z6 = len([p for p in rows[row+1] if int(p.x) == col-1])+z6d \
           if rows.has_key(row+1) else z6d
        z7 = len([p for p in rows[row+1] if int(p.x) == col])+z7d \
           if rows.has_key(row+1) else z7d
        z8 = len([p for p in rows[row+1] if int(p.x) == col+1])+z8d \
           if rows.has_key(row+1) else z8d
        cell.calc_region (particles=[p for p in particles if int(p.x) == col],
                          z=[z0,z1,z2,z3,z4,z5,z6,z7,z8,])
      for p in [p for p in particles if row < self.height and p.x > 0 and p.x < self.width]:
        # appyl force
        p.next ()
        # redraw if necessary
        if p.dirty:
          p.erase()
          p.draw()
    self.particles = [p for p in self.particles if p.active]

  def calc_force(self):
    self.force = max([self.xforce,self.xforce*-1])+max([self.yforce,self.yforce*-1])

def main():
  session = getsession()

  # n away from leftside screen
  e=lambda x: session.width-x
  pg = Playground(session.width, session.height,
    pystarts=[1,2,2,3,3,3], pxstarts=[5,5,5,4,4,6,6,3,7,e(5),e(5),e(5),e(4),e(4),e(6),e(6),e(7),e(7)],
    pxforces=[-0.5,0.5,-1.0,-1.0,-1.25,1.25], pyforces=[0.2,0.3,0.4],
    pps=10)

  while True:
    x = readkey(0.1)
    if x == 'q':
      disconnect()
    echo (pos(1,1))
#    for particle in pg.particles:
#      print 'x,y=', particle.x, particle.y, 'force=',particle.xforce, particle.yforce
#      print particle.xl, particle.yl, particle.dirty
#      print
#    x = readkey()
#    echo (cls())
    if x == 'q':
      disconnect()
    pg.next()


#def main ():
#  session = getsession()
#  topdrops = 1000
#  water = Water(session.height -1, 1, session.width, session.height/2)
#  drops = [Drop(session.height, session.width) for n in range(topdrops/100)]
#  while True:
#    for drop in drops:
#      drop.draw()
#    x = readkey(0.2)
#    if len(drops) < topdrops:
#      drops.append (Drop(session.height, session.width))
#    if x == 'q':
#      disconnect()
#    n_drops = []
#    for drop in drops:
#      drop.erase()
#      drop.next()
#      if drop.y >= water.top:
#        if water.rise():
#          water.draw ()
#        n_drops.append (Drop(session.height, session.width))
#      else:
#        n_drops.append (drop)
#    drops = n_drops
#



    # grow or destroy the cell edges to current playground width/height
    #for row in range(self.height, height):
    #  if row == self.height:
    #    # remove the 'rock bottom'...
    #    for col in range(self.width):
    #      cells[row,col].density = 0.0
    #  for col in range(self.width):
    #    cells[(row,col)] = Cell(row,col)
    #    if row == height:
    #      # set new 'rock bottom'...
    #      cells[(row, col
    #  cells[row,c in range(self.width)]
    ## and a rock bottom...
    #for col in range(width):
    #  cells[height-1].density = 1.0


