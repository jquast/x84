"""
Game database for Sword of the Samurai.

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = 'Copyright (c) 2007, 2008 Jeffrey Quast'
__version__ = '$Id: gamedb.py,v 1.1 2008/07/03 00:56:41 dingo Exp $'
__license__ = 'Public Domain'
import random

deps = ['bbs', 'games/sots/data_text', 'games/sots/data_province']
import db
import operator

debugKill=0 # set True to always rebuild fresh database

class GameTextClass(dict):
  " not sure where im going with this :) "
  def __init__(self, gameText=None):
    if gameText:
      self.defaultGameText =gameText
    else:
      self.defaultGameText = defaultGameText
    dict.__init__(self, gameText)
  def __setattr__ (self, key, value):
    self[key] = value
  def __getattr__ (self, key):
    try:
      return self[key]
    except KeyError:
      if self.defaultGameText.has_key(key):
        return self.defaultGameText[key]
      raise KeyError, key

def init():
  """
  Load game databases and repositories using L{db.openudb()}.

  Repositories are created if nonexistant or if L{debugKill} is set to C{True}
  """
  global provinces
  global samurais
  global text
  gamedb = openudb('sots')
  text = GameTextClass (defaultGameText)

  if not gamedb.has_key('provinces') or debugKill:
    print "gamedb without 'provinces'"
    rebuild_provinces ()
  provinces = gamedb['provinces']

  if not gamedb.has_key('samurais') or debugKill:
    print "gamedb without 'samurais'"
    rebuild_samurais ()
  samurais = gamedb['samurais']

##
# Provinces
##

def rebuild_provinces():
  " Rebuild L{provinces} repository. "
  global provinces
  gamedb = openudb('sots')
  if gamedb.has_key('provinces'):
    del gamedb['provinces']
  gamedb['provinces'] = db.PersistentMapping ()
  gamedb['provinces'].__creationtime = timenow ()
  for pkey in defaultProvinces.keys():
    gamedb['provinces'][pkey] = Province (pkey)
    newProvince = gamedb['provinces'][pkey]
    for pattr in defaultProvinces[pkey]:
      newProvince.set(pattr, defaultProvinces[pkey][pattr])
    newProvince.set('creationtime', timenow())
    #print newProvince.__secret__, '-'*80
  provinces = gamedb['provinces']

class Province(db.PersistentMapping):
  """
  Province Class for Sword of the Samurai.
  """

  def __init__(self, provinceName):
    """
    @param provinceName: A unique province name, becomes record key
    """
    db.PersistentMapping.__init__(self, {'name': provinceName})
    self['creationTime'] = timenow()
    self['members'] = []
    for key in ('honor','generalship','swordsmanship','land'):
      self[key] = 0
    self['clan'] = ''
    self['hatamoto'] = ''
    self['neighbors'] = ''

  def __repr__(self):
    return '<Province:%s>' % \
      ['%r:%r' % (key, self[key]) for key in self.keys()]

  def __getattr__(self, name):
    try:
      return PersistentMapping.__getattr__(self, name)
    except AttributeError, e:
      try:
        return self.__getitem__(name)
      except KeyError:
        raise AttributeError, e

  def set(self, key, value):
    " Set key, value of province record."
    self[key] = value
    #commit ()

  def save(self):
    " Save province record to the database "
    provinces[self.name] = self
    commit ()

  def delete(self):
    " Remove this province record from database."
    if provinces.has_key(self.name):
      del provinces[self.name]
      return True
    return False

  def addMember (self, samurai):
    " Add reference to samurai as member of this province."

    if not self.has_key('members'):
      print 'sots: first new member of %s: %s' % (self.name, samurai.handle)
      self.set ('members', [])

    if not samurai.handle in self.members:
      self.set ('members', self.members + [samurai.handle])
      samurai.joinProvince (self.name)
      return True
    return False

  def removeMember (self, samuraiKey):
    " Remove reference to samurai as a member of this province. "
    members = self.members
    if samuraiKey in members:
      members.remove (samuraiKey)
      self.set ('members', members)
    else:
      return False

  def print_honoraries(self):
    " return string details of province honorables "
    return implode([ \
      text.honor[int(self.honor)] + ' honor',
      text.honor[int(self.generalship)] + ' generalship',
      text.honor[int(self.swordsmanship)] + ' swordsmanship',
      text.size[int(self.land)] + ' land'])

  def print_details(self):
    " Return string details of a province's qualities and members, if any. "
    print self
    ret = '%s Province of the Clan %s has %s.\n\nNeighboring provinces are: %s.\n\t' \
        % (self.name, self.clan, self.print_honoraries(), implode(self.neighbors))
    if len(self.members):
      ret += '\nThere are %s members of this province:' % len(self.members)
      for member in self.members:
        samurai = samurais[member]
        if member != provinces[samurai.province].hatamoto:
          ret += '\n   - ' + samurai.print_rankDescription()
    return ret

  def getMembers(self, levels=(1,)):
    """
    Return samurais in province, optionaly sorted by ranking (score).

    @param excludeSelf: samurai key to exclude from list.
    @param byRank: set True to return in ascending rank order.
    """
    members = self.members

    slist = [(s.score(), s.handle) \
             for s in [samurais[m] for m in members]
             if s.level in levels]
    slist.sort ()

    # make descending order
    swp = [handle for score, handle in slist]
    swp.reverse ()
    return swp

  def chkCreateHatamoto(self):
    " check for and create a hatamoto (lord) for this province "
    depth = 0
    while not self.hatamoto and depth < 50:
      hatamotoName = random.choice(text.familyname)
      if hatamotoName in self.members:
        print 'sots:', hatamotoName, 'is taken.'
        depth += 1
        continue

      print 'sots:', hatamotoName, 'is new hatamoto of', self.name
      h = Samurai (hatamotoName)
      h.name = hatamotoName
      h.handle = hatamotoName
      h.ai = True
      h.level = 2
      h.province = self.name
      h.age = random.choice([4,5])
      h.location = 'home'

      # set random values, use province values for high and low limits
      for key in ['honor','generalship','swordsmanship','land']:
        h.set (key, self[key])
      h.save ()
      self.addMember (h)

      # set our new hatamoto reference
      self.set ('hatamoto', hatamotoName)
      print "%s's new hatamoto: %s" % (self.name, hatamotoName)

    if depth >= 50:
      print 'XXX sots: reached maximum depth'

  def chkCreateSamurais(self,  members=4):
    """
    Generate minimum number of ai samurai for province.

    @todo: generate marriage and children.
    """

    while len(self.members) < members:
      subordinateName = random.choice(text.familyname)
      if subordinateName in self.members:
        print 'sots:', subordinateName, 'is taken.'
        continue
      print 'sots:', subordinateName, 'is new subordinate of', self.name

      # create subordinate ai samurai
      s = Samurai (subordinateName)
      s.set ('ai', True)
      s.set ('name', subordinateName)
      s.set ('age', random.choice([2,3,4,5]))
      s.set ('aggression', random.choice([0,0,0,1,1,2]))
      s.set ('level', 1)
      s.set ('location', 'home')
      # TODO: generate marriage, love, and children!

      # set random values, use province values for high and low limits
      for key in ['honor','generalship','swordsmanship','land']:
        low, high  = self[key] -1, self[key] +3
        if low < 1.0: low = 1.0
        if high > 7.0: high = 7.0
        s.set (key, int(random.uniform(low, high)))

      # calculate number of warriors, 30-100% of maximum possible
      numWarriors = int(random.uniform(s.maxWarriors()*.3, s.maxWarriors()))
      s.set ('warriors', int(numWarriors))

      # add subordinate to province
      s.joinProvince (self.name)

      # add subordinate to samurai db
      s.save ()

  def makeLowestRank(self, samurai):
    print 'make lowest ranked'
    print [h for h in self.members if samurais[h].ai]
    print '-'*80
    # for each ai player in province,
    for ai in [h for h in self.members if samurais[h].ai]:
      print ai
      aiSam = samurais[ai]
      # as long as their score is less than ours
      while aiSam.score <= samurai.score():
        # bump ai's score up by improving random stats
        print 'bump aiSam score', aiSam.score(), \
              'above our score,', samurai.score()

        attr = random.choice (['generalship','honor','swordsmanship','warriors'])
        value = aiSam[attr]
        print 'bump?', attr
        if attr == 'warriors':
          if value < aiSam.maxWarriors():
            # add (1) warrior
            aiSam.set(attr, value+1)
            print 'bumped'
        elif value < 7.0:
          # add 0.1 to attribute value
          aiSam.set(attr, value +0.1)
          print 'bumped'


def listProvinces():
  " return all province records in the database "
  return [provinces[key] for key in provinces.keys()]

def provinceExist(name):
  " return True if province exists "
  return name in provinces.keys()

## Samurais
#

def rebuild_samurais():
  " Rebuild L{samurais} repository. "
  global samurais
  gamedb = openudb('sots')
  gamedb['samurais'] = db.PersistentMapping ()
  gamedb['samurais'].__creationtime = timenow ()
  samurais = gamedb['samurais']

class Samurai(db.PersistentMapping):
  """
  Samurai Class for Sword of the Samurai.
  """

  def __init__(self, handle):
    """
    @param handle: unique key for samurai record. Not the same as samurai.name
    """
    db.PersistentMapping.__init__(self, {'handle': handle})
    self['creationtime'] = timenow()
    self['honor'] = 0
    self['generalship'] = 0
    self['swordsmanship'] = 0
    self['land'] = 0
    self['warriors'] = 0
    self['province'] = None
    self['heir'] = None
    self['children'] = []

  def __repr__(self):
    return '<Samurai:%s, %s>' % \
      (self.name, ['%s:%s' % (key, self[key]) for key in self.keys()])

  def __getattr__(self, name):
    try:
      return PersistentMapping.__getattr__(self, name)
    except AttributeError, e:
      try:
        return self.__getitem__(name)
      except KeyError:
        raise AttributeError, e

  def joinProvince(self, provinceName):
    if provinceExist(provinceName):
      self.set('province', provinceName)
      provinces[provinceName].addMember (self)

  def set(self, key, value):
    " Set key, value of samurai record. "
    self[key] = value
    #commit ()

  def save(self):
    " Create a new samurai record in the database "
    samurais[self.handle] = self
    commit ()

  def delete(self):
    " remove this samurai record from database "
    # first, delete samurai from province
    if self.has_key('province') \
    and provinceExist(self.province):
      provinces[self.province].removeMember(self.name)

    if provinces.has_key(self.name):
      del provinces[self.name]
      return True
    return False

  def delete(self):
    " remove samurai record from database "
    del samurais[self.handle]

  def maxWarriors(self):
    """
    Return maximum number of warriors this samurai may have
    accordingly to size of fief.
    """
    # XXX balance
    return int((self.land * 14.0) * (self.level * 1.0))

  def score(self):
    return int(self.honor*10 \
             + self.generalship*10 \
             + self.swordsmanship*10 \
             + self.land*10 \
             + (self.warriors/14.0)*3.0)

  def printGressHonor(self):
    if self.aggression:
      ret = an(text.aggression[self.level].lower())
    else:
      ret = 'a'
    return '%s %s of %s honor' % \
      (ret, text.level[self.level].lower(),
       text.honor[int(self.honor)])

  def getRank(self):
    rankedMembers = provinces[self.province].getMembers()
    return rankedMembers.index(self.handle)

  def print_rankDescription(self):
    """
    Return printable description of samurai

    @todo: an() helper, you(), any other helper to trim down this awful codesize!
    """

    if self.handle == handle():
      ret = 'You are a '
      ourself = True
    else:
      ret = self.name + ' is a '
      ourself = False

    ranking = self.getRank()

    # highest ranked samurai
    if ranking == 0:
      ret += '%s of great renown. ' \
        % text.level[self.level].lower()
      if ourself: ret += 'You control '
      else: ret += 'He controls '
      ret += 'a %s fief, and command' % text.size[int(self.land)]
      if not ourself: ret += 's'
      ret += ' %s warriors; ' % self.warriors
      if ourself: ret += 'You are '
      else: ret += 'he is '
      ret += 'known throughout the province as %s.' \
        % self.printGressHonor()

    # 2nd highest ranking
    elif ranking == 1:
      ret += 'promising %s who has a %s fief and %s warriors. ' \
        % (text.level[self.level].lower(), text.size[int(self.land)],
           self.warriors)
      if ourself: ret += 'You are %s.' % self.printGressHonor()
      else: ret += 'He is %s.' % self.printGressHonor()

    # third highest ranking
    elif ranking == 2:
      ret += '%s of no great distinction and %s honor who controls ' \
             'a %s fief and %s warriors.' \
        % (self.printGressHonor(), text.honor[int(self.honor)],
           text.size[int(self.land)], self.warriors)

    # no significant rank
    else:
      if ourself:
        ret = 'You have '
      else:
        '%s has ' % self.name
      ret += 'a %s fief, and command'
      if ourself:
        ret += 's'
      ret += ' %s warriors. '
      if ourself:
        ret += 'You are known as %s.' % self.printGressHonor()
      else:
        ret += 'He is known as a %s.' % self.printGressHonor()

    return ret + ' (%s)' % self.score()

def samuraiExist(handle):
  " Return C{True} if samurai record exists by key C{handle}."
  return samurais.has_key(handle)

def listSamurais():
  " Return all samurai database records."
  return [samurais[skey] for skey in samurais.keys()]

def listSamuraiNames():
  " Return names of all samurai records. "
  return [samurai.name for samurai in listSamurais()]
