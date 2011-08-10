"""
Event subsystem for Sword of the Samurai.

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = 'Copyright (c) 2007, 2008 Jeffrey Quast'
__version__ = '$Id: events.py,v 1.1 2008/07/03 00:56:41 dingo Exp $'
__license__ = 'Public Domain'
import random
# PRSV db required for db.Persistent's in global class definition
import db

deps = [
  'bbs',
  'games/sots/data_province',
  'games/sots/data_text',
  'games/sots/gamedb']

debugKill=0 # set True to always rebuild fresh database

def init():
  global events
  gamedb = openudb('sots')
  # initialize/open events database
  if not gamedb.has_key('events') or debugKill:
    print "gamedb without 'events'"
    gamedb['events'] = db.PersistentMapping ()
  events = gamedb['events']

def info(text):
  " display text in a box located randomly somewhere on the screen "
  w=40
  echo (cls())
  pw = paraclass(ansiwin(y=1, x=1, h=23, w=w), split=8, ypad=2, xpad=2)
  pw.update (text, refresh=False)
  h = pw.adjheight ()
  pw.ans.y = int(random.uniform(4, 24-h))
  pw.ans.x = int(random.uniform(10, 60-w))
  pw.ans.lowlight (partial=True)
  pw.refresh ()
  pw.ans.title('press any key', align='bottom')
  readkey ()

class Event(db.Persistent):
  """
  A Persistent game event queue for Sword of the Samurai
  """
  def __init__(self, handle):
    self.handle = handle
    self.queue = db.PersistentList()

  def _save(self):
    gamedb['events'][self.handle] = self

  def append(self, *eventArgs):
    " Place event on top of stack stack, first one popped off "
    self.queue.append ((eventArgs[0],) +eventArgs[1:])

  def push(self, *eventArgs):
    " Push event into front of stack queue, last one popped off "
    self.queue.insert (0, (eventArgs[0],) +eventArgs[1:])

  def pop(self, retrieve=None):
    " Pop event off top of queue, or foremost event that matches L{retrieve}."
    print "Popping event off queue:"
    print self.queue

    if not len(self.queue):
      # when no events exist in stack, append a Home event
      return (Event.home, (None,),)

    if retrieve:
      for index, waiting_event in enumerate(self.push):
        if waiting_event[0] == retrieveEvent:
          return self.queue.pop (index)

    return self.queue.pop ()

  ##
  # Spin the wheel of time
  ##
  def nextTurn(self, *args):
    " turn forward time, AI thinks here... "
    zen = random.choice(text.pause)
    echo (cls() + color() + pos(center(pause()), 12) + zen)
    readkey (0.5)

  ##
  # Modifiers
  ##

  def increaseGeneralship(self, change):
    " Increase the generalship of our samurai. "
    self.samurai.set ('generalship', self.samurai.generalship +change)
    self.push (Event.chkClanRating, (None,))

  def increaseSwordsmanship(self, change):
    " Increase the swordsmanship of our samurai. "
    self.samurai.set ('swordsmanship', self.samurai.swordsmanship +change)
    self.push (Event.chkClanRating, (None,))

  def increaseHonor(self, change):
    """
    Increase the honor of our samurai. The hatamoto praises that samurai and
    gives a hinting to that samurai's rating.
    """
    self.samurai.set ('honor', self.samurai.honor +change)
    self.push (Event.chkClanRating, (None,))

    self.push (Event.honorableAct, (self.samurai,))
    self.push (Event.chkClanRating, (None,))
    #province.broadcastEvent(Event.honorableAct, self.samurai)

  def increaseLand(self, change):
    self.samurai.set ('land', self.samurai.land +change)
    self.push (Event.chkClanRating, (None,))
    info ('A small amount of land is added to your control. You are ' \
      'now responsible for a ' + text.size[int(self.samurai.land)] + ' fief.')

  def decreaseHonor(self, change):
    self.samurai.set ('honor', self.samurai.honor -change)
    self.push (Event.chkClanRating, (None,))

  def decreaseLand(self, samurai, change):
    samurai.set ('land', samurai.land -change)
    self.push (Event.chkClanRating, (None,))

    if samurai.warriors <= samurai.maxWarriors():
      # samurai still has enough rice patties to support his warriors :)
      return

    if samurai.warriors > self.samurai.maxWarriors():
      # cannot maintain warriors with these rice paddies
      loss = self.samurai.maxWarriors() -self.samurai.warriors
      self.samurai.set ('warriors', self.samurai.warriors -loss)
      self.push (Event.samuraiLossByLand, (self.samurai, loss))

    if samurai.handle == handle():
      info ('This action costs you a small amount of land. ' \
            'Your remaining land holdings are %s.' \
            % text.size[int(self.samurai.land)])

  def announceVictory(self, samurai):
    info ('Another victory for %s clan! %s has ' \
          'defeated the enemy forces, and %s has ' \
          'awarded him a moderate piece of the conquered ' \
          'territory.' \
          % (provinces[samurai].clan, samurai.name, \
             provinces[samurai].hotomoto))

  ##
  # Notices
  ##
  def noticeIncreasedWarriors(self, samurai, change):
    info ('%s has added %s samurai to his army.' \
          % (samurai.name, change))

  ##
  # Quests: Origins
  ##

  # Quest: Village Bandits
  def villageBandits(self, *args):
    # quest.add()
    txt = 'Word from Lord %s: a group of bandits is marauding the ' \
          'peasants\' villages. Lord %s would look with favor upon ' \
          'one who exterminated these foul pests; volunteers should ' \
          'call on him at his castle.' % self.province.hatamoto

  # Quest: Capture Garrison
  def announceGarrisonCapture(self, province, neighboringProvince):
    info ('Lord %s would be pleased if a certain fortress in %s with ' \
          'a very large garrison were captured. Anyone interested in ' \
          'this task should come to Lotd %s castle.' \
          % (province.hatamoto, neighboringProvince.name,
             ownership(province.hatamoto)))

  # Quest: Besieged Border Fortress
  def besiegedFortress(self, enemy):
    info ('A border fortress is besieged by a %s force of ' \
          'sohei who have laid claim to that area. These monks ' \
          'should be forced to return to their own temple lands. ' \
          'Volunteers should call upon Lord %s.' \
          % (text.size[int(enemy.warriors /10)],
             self.province.hatamoto))

  # Quest: Abducted priest
  def priestAbducted(self, province):
    # Province-wide announcement
    info ('An envoy from %s says that a rebellious band of peasants has ' \
          'abducted a priest and threatens to kill him unless all peasants\' ' \
          'debts to moneylenders are canceled. Is there no one brave enough ' \
          'to rescue the priest? Such a one should call on %s at his castle.')

  # Quest: Quell Invading Force
  def quellInvaderPlea(self, enemy):
    info ('Lord %s declares that %s of the neighboring ' \
          '%s province is sowing the seeds of a large invasion ' \
          'force. A storm should destroy this crop before it ' \
          'ripens. One undertaking this task should march to ' \
          'Lord %s castle.' \
          % (self.province.hatamoto, enemy.province,
             ownership(self.province.hatamoto)))
    # if this is not quelled in so many turns, it becomes an active
    # province-wide invasion?

  # Quest: Bandits Menacing Bandints
  def roninMenacing(self, province):
    info ('A band of ronin has been menacing travelers on the high road. ' \
          'The one who brought an end to these outrages would surely be ' \
          'regarded as a hero. Those wishing to show their mettle should ' \
          'call on the Lord %s at his castle.' \
          % province.hatamoto)

  # Quest: Captured Assassin
  def lordAssasinCaught(self, *args):
    # Province-wide announcement
    info ('An assasin sent to slay Lord %s has been cornered in a ' \
          'tower room of Lord %s castle. One courages enough to ' \
          'engage this assassin in single combat would surely gain ' \
          'much honor.' % (self.province.hatamoto,
            ownership(self.province.hatamoto)))

  # Quest: Samurai Challanger
  def newChallanger(self, *args):
    # Province-wide announcement
    info ('A strange samurai of surpassing skill has appeared at ' \
          'Lord %s castle. He calls for a challenger to duel with ' \
          'him to defend the honor of the clan.' % (self.province.hatamoto))

  # Quest: Abducted Priest
  def priestAbducted(self, *args):
    info ('Desperate peasants hold the priest in a house near a rice field. ' \
          'Determined to succeed or die, you draw your sword and attack.')

  # Quest: Pass being held to neighboring Province
  def passHeld(self, enemy):
    info ('%s says, "A %s body of enemy troops holds the pass into %s. ' \
          'Who will sweep them away for me?" He will receive volunteers ' \
          'at his castle.' \
          % ( self.province.hatamoto, enemy.province,
              text.size[int(enemy.warriors /10)]))

  ##
  # Quest: Accepting Challenge
  ##

  # Quest: Quell Invading Force
  def attackEnemyClan(self, enemy):
    info ('You march over the border to attack the clan\'s enemy. ' \
          '%s knew you were coming, and has arrayed his forces to ' \
          'meet you. You form up your own troops, then give the order ' \
          'to attack!' % enemy.name)

  # Quest: Campaign, outlook bad??
  def announcePoorCampaign(self, enemyProvince):
    info ('Lord %s is planning another campaign against %s ' \
          'clan, but it is said that this time he is greatly ' \
          'outnumbered.' % (province.hatamoto, enemyProvince.clan))

  # Quest: Besieged Border Fortress by Monks
  def announceBesiegedFortress(self, samuraiName):
    # announce a samurai who begins facing the monks
    info ('%s is facing the rebellious monks.' % samuraiName)
    info (txt)
    #followed by announceVictory when sucessfull

  # Quest: Seige Enemy Clan's Fortress
  def seigeClanFortress(self, *args):
    info ('You march to the enemy\'s fortress. The enemy is well defended ' \
          'behind the walls and earthworks, but the strongest fort may ' \
          'fall to a determined attacker. You give the order, and your ' \
          'troops surge forward!')

  # Quest: Village Bandits
  def assistFendingBandits(self, samurai):
    info ('Your offte to help %s is graciously accepted. Indded, he urges ' \
          'you to accept the generalship of the combined forces. Together you ' \
          'are certain to rout the intruders.' % samurai.name)
    info ('Under your leadership, the combined forces rout the invaders. ' \
          'Together, you and %s survey the heads of your defeated foes.')

  # Quest: Captured Assassin
  def attackAssassin(self, *args):
    info ('"Stay out!" the assassin screams. "Enter this room, ' \
          'and you die!" Obviously he knows nothing of honor. ' \
          'Sword held before you, you leap into the room to face ' \
          'him.')

  # Quest: Samurai Challanger
  def attackChallenger(self, *args):
    return

  # Quest: Menacing Bandits
  def attackRonin(self, *args):
    txt = 'You accompany a group of travelers as it leaves the castle. ' \
          'The band of rogue ronin appears, and arrogantly starts across ' \
          'the rice paddies toward you. You draw your sword and move to ' \
          'meet them.'
    info (txt)
    txt = 'The masterless samurai fall before your flashing blade, and a ' \
          'stain on the honor of clan %s is removed.\r\n'
    info (txt)
    # increase honor

  # Quest: Pass being held to neighboring Province
  def attackHeldPass(self, *args):
    info ('Your army marches to the pass that is blocked by the enemy. ' \
          'You address your troops: "Think only of your enemy, not of ' \
          'yourself. To think of losing is to lose! Set your mind to ' \
          'victory! Now, attack!"')

  # Quest: Pass being held to neighboring Province
  def announceAttackHeldPass(self, samuraiName):
    info ('%s is attempting to clear the pass.' % samuraiName)

  ##
  # Quest: Victories
  ##

  # Quest: Pass being held to neighboring Province
  def captureHeldPass(self, *args):
    info ('Word comes from Lord %s as you view the heads of your defeated ' \
          'enemies: you are to be rewarded by adding a moderate piece of ' \
          'the captured territory to your fief.' \
          % self.province.hatamoto)

  # Quest: Seige Enemy Clan's Fortress
  def seigedClanFortress(self, *args):
    info ('Victorious, you raise a pennant with the symbol of clan %s' \
          'over the fortress. Lord %s rewards you by adding a large ' \
          'piece of the captured territory to your fief.' \
          % (self.province.clan, self.province.hatamoto))

  # Quest: Samurai Challanger
  def defeatedChallenger(self, *args):
    info ('You have preserved the honor of the %s clan. Word of your ' \
          'victory is spread far and wide.' % self.province.clan)
    inc = self.samurai.honor *.10 # gain 15% honor
    if inc < .25: # at least .25
      inc = .25
    if inc > .75: # no more than .75
      inc = .5
    self.push(Event.increaseHonor, (inc,))

  # Quest: Quell Invading Force
  def defeatedEnemyClan(self, enemy):
    info ('The enemy flees before your victorious forces - the power ' \
          'of %s is broken! Lord %s rewards you by adding a moderate ' \
          'piece of the captured territory to your fief.' \
          % (provinces[enemy.province].clan, self.province.hotomoto))
    inc = self.samurai.honor *.10 # gain 10% honor
    if inc < .20: # at least .20
      inc = .20
    if inc > .5: # no more than .5
      inc = .5
    self.push(Event.increaseHonor, (inc,))

  # Quest: Abducted Priest
  def savedAbductedPriest(self, *args):
    info ('The priest is most grateful for being freed. "I will tell ' \
          'everyone I meet of your courage and awesome skill. It is a ' \
          'privilege to be rescued by a samurai such as you."')
    inc = self.samurai.honor *.25 # gain 25% honor
    if inc < .50: # at least .50
      inc = .50
    if inc > 1: # no more than 1
      inc = 1
    self.push(Event.increaseHonor, (inc,))

  ##
  # Quest: Failures
  ##

  # Quest: Abducted Priest
  def failedSavingPriest(self, samurai):
    info ('%s tried to save the priest held hostage by the peasants, but ' \
          'was killed in the attempt. Of %s, Lord %s later said, "He knew ' \
          'his duty, and I honor him no less because he failed to achieve ' \
          'his goal."')

  ##
  # Feif Activity: Origins/Please
  ##

  def segieHelp(self, samuraiName, enemy):
    info ('Message from %s: "My fief is under attack by a %s ' \
          'group of %s samurai. I regard this, not as misfortune, but ' \
          'as an opportunity for glory!"\n' \
          'He rushes home to take personal command of his warriors. ' \
          '%s urges all true samurai to join him in crushing the invaders.' \
          % (samuraiName, text.size[int(enemy.warriors /10)],
             samuraiName))

  def underRebellionAttack(self, samurai, rebellion):
    info ('A %s unit of Ikko-ikki is attacking the holdings ' \
          'of %s, inflaming the peasants and calling for his overthrow.\n' \
          '%s urges all true samurai to join him in crushing the invaders.' \
          % (text.size[int(rebellion.warriors)/10],
             samuraiName, samuraiName))

  def rebellionAttack(self, rebellion):
    info ('A %s unit of Ikko-ikki has entered your lands and ' \
          'is inflaming the peasants to rebellion. These fanatical ' \
          'scum must be exterminated!\n' \
          'You announce your eagerness for the coming battle.' \
          % text.size[int(rebellion.warriors)/10])

  def banditPlea(self, samurai):
    info ('A large gang of bandits menaces the peasants in %s fief.\n' \
          '%s urges all true samurai to join him in crushing the invaders.' \
          % (ownership(samurai.name), samurai.name))

  ##
  # Fief Activity: Activities
  ##

  def underSeige(self, enemy):
    info ('Gathering your faithful retainers, you prepare to defend ' \
          'your lands against the intruders.')

  def inciteRebellion(self, enemy):
    info ('More than anyone else, the peasants hate and fear %s tax ' \
          'collector. If you can find him and slay him, this may incite ' \
          'the peasants to risde up and defy their lord.' \
          % ownership(enemy.name))
    info ('Freed of the tax collector, and realizing that the entire ' \
          'village will be punished for his death, the peasants rise up ' \
          'and declare themselves independent of their samurai lord. It ' \
          'will be expensive for %s to put them back in their place.' \
          % enemy.name)

  def defendRebellionAttack(self, enemy):
    info ('Gathering your faithful retainers, you prepare ' \
          'to defend your lands against the intruders.')
    # battle
    # increase generalship if won,
    # decrease land if lost

  ##
  # Fief Activity: Victories
  ##

  def wonRebellionAttack(self, loss):
    info ('You repel the invaders, but lose %s samurai in doing so.')

  def intruderVictory(self, samurai):
    info ('%s has driven the intruders from his domain.\n' \
          'It is good to see %s do an honorable deed. %s is ' \
          'a samurai of %s honor.' \
          % (samurai.name, samurai.name, samurai.name,
             text.honor[int(samurai.honor)]))

  def banditsAttackDeflected(self, samurai):
    info ('%s has driven of off the bandits who plagued the villages.' \
          % samurai.name)

  ##
  # Fief Activity: Failures
  ##

  def lostRebellionAttack(self, *args):
    info ('The invaders, having resisted all attempts to expel ' \
          'them, now occupy a portion of your lands. Your holdings ' \
          'are now diminished by a very small amount.')

  ##
  # Marriage
  ##

  def announceMarriage(self, samurai, bride):
    info ('%s has married %s in a traditional ceremony.' \
      %s (samurai.name, bride.name))

  def marryBride(self, bride):
    info ('Arrayed in your finest garments, you and your chosen bride ' \
          'are married by a Shinto priest before a gathering of family ' \
          'and retainers. The day is a whirl of gifts from friends and ' \
          'admirers, fine speeches and poems, and best of all the shy, ' \
          'adoring glances of your new wife.')

    self.samurai.set ('wife', bride.handle)

    # forfiet land for brides' family
    rm = self.samurai.land /4 # 25% decrease in land
    if rm >1.0: rm = 1.0 # no more than 1
    elif rm < .50: rm = .50 # no less than .50
    if self.samurai.land -rm < 1: # donate remaining land
      rm = self.samurai.land -1
    self.push (Event.decreaseLand, (self.samurai, rm,))

  ##
  # Courting
  ##

  def pursueKidnappedBride(self, bride):
    # minigame, if won, marry, if lost, death!
    self.push(Event.marryBride, (bride,))

  def kidnappedBride(self, bride):
    echo (cls() + '\r\nWoe! The matchmaker reports that %s went to ' \
          'view a nearby waterfall and was kidnapped by bandits! ' \
          'They have been traced to an abandoned castle. If you save ' \
          'her, you will be regarded as an excellent prospect for ' \
          'a match.\r\n' \
          'You decide to\r\n' % bride.name)
    echo ('  e: Enter the bandits\' lair and rescue %s.\r\n' % bride.name)
    echo ('  d: Decline due to pressing concerns at home.\r\n')
    while True:
      ch = readkey()
      if ch == 'e':
        self.push(Event.pursueKidnappedBride, (bride,))
        return
      elif ch == 'd':
        self.push(Event.enterCastle, (self.province.hatamoto,))
        return

  def courtBride(self, bride):
    # remove bride availability
    if random.choice([0,1]):
      # chance to fight for her if in castle
      self.push (Event.kidnappedBride, (bride,))
      return

    self.push (Event.marryBride, (bride,))

  def offeredBride(self, bride):
    txt = 'You are approached by a matchmaker. "I have the ' \
          'perfect bride for you," he says, "a modest woman ' \
          'from a family of %s honor who has been well ' \
          'trained in the skills of household management. Her ' \
          'name is %s, and her father requires only a moderate ' \
          'gift of land. She awaits suitors at %s castle. ' \
          % (text.honor[int(bride.honor)], bride.name,
             plural(provinces[bride.province].hatamoto))
    info (txt)

  def matchMaker(self, *args):
    # Find unmarried women from pool,
    # if none, create one,
    # create bride quest
    # bride quest sends to all unmarried men offeredBride event,
    return

  ##
  # Reproduction
  ##

  def bornDaughter(self, *args):
    info ('You receive word that your wife has borne you a daughter. ' \
          'You pray to your ancestores that she may be blessed with ' \
          'a happy life and an advantageous marriage.')

  def nameSon(self, son):
    echo ('\r\nYou call your son: ')
    while True:
      newName = readline (15, son.name)
      if not newName: continue
      break
    son.set ('name', newName)

  def bornSon(self, *args):
    # son = child(gender=MALE)
    echo (cls() + '\r\nYou receive word that your wife has borne you a son. ' \
          'An heir to the house of %s! You are filled with warmth and bright ' \
          'joy, as if the sun had risen in your heart. Your wife humbly ' \
          'suggests %s as a name.\r\n' % son.name)
    echo ('  a: Accept %s as a fine name.\r\n' % son.name)
    echo ('  n: Name your son yourself.\r\n')
    while True:
      ch = readkey()
      if ch == 'a':
        return
      if ch == 'n':
        self.push (Event.nameSon, (son,))
        return

  ##
  # Threats
  ##

  def acceptThreat(self, *args):
    echo (cls() + '\r\nYou receive a message from %s: "It is good to have ' \
          'a family to carry on one\'s name. My advice is to guard your ' \
          'family carefully. I ask no payment for this fine advice, but ' \
          'would it not be fitting to acknowledge a debt equal to its ' \
          'worth?" You decide to\r\n')
    echo ('  s: Send him the wealth from a tiny piece of land.\r\n')
    echo ('  i: Ignore these thinly-veiled threads.\r\n')
    while True:
      ch = readkey()
      if ch in ['s','i']: return

  def veieldPraise(self, enemy):
    txt = 'Your praise for %s is noted at court. Some feel that, ' \
          'if you praise him, %s must be a worth samurai; his honor ' \
          'improves. Others wonder that you would associate yourself ' \
          'with such as he; your reputation is somewhat diminished.' \
          % enemy.name
    info (txt)
    # increase enemy honor
    # decrease our honor

  ##
  # Death, Dying, and Heir
  ##

  def victoriousDuel(self):
    info ('It is over; your opponent lies dead on the ground before ' \
          'you. Truly, life is no more lasting than a flower in the ' \
          'spring.')

  def assumeLeadership(self, samurai):
    info ('%s heir, %s, has assumed leadership of his house.' \
      % (samurai.replaced, samurai.name))

  def nearDeath(self, *args):
    info ('You try to force your body to keep attacking, but the ' \
          'wounds you have taken are too great, and the world goes ' \
          'black. When you awaken, your wounds have been tended and ' \
          'bound, but nothing can soothe the shame that burns in your ' \
          'heart.')

  def lordDeathByBattle(self, hatomoto):
    info ('Lord %s was killed leading his troops in an attack on an ' \
          'enemy clan. Who is worthy enough to replace him?')

  def abdicated(self, retiredSamurai):
    info ('%s has abdicated in favor of his heir, ' \
          'withdrawing from public affairs to become a monk.' \
          % reitredSamurai.name)
    info ('%s heir, %s, has assumed leadership of his house.' \
          % (retiredSamurai.name, retiredSamurai.heir))

  ##
  # Traveling & Encounters
  ##

  def travelingAlone(self, samuraiName):
    info ('%s is traveling by himself. He said, "If it is my fate ' \
          'to win honor on this journey, will it not be greater if ' \
          'I do so alone?"' % samuraiName)

  def troopMovement(self, samuraiName):
    info ('%s and his troops are on the move.' % samuraiName)

  def travel(self, *args):
    self.samurai.activity = 'Considering a course of action'
    echo (cls() + '\r\nConsidering your plan of action, you decide to\r\n')
    echo ('   a: travel alone, testing yourself against fate.\r\n')
    echo ('   p: travel disguised as a poor ronin.\r\n')
    echo ('   h: travel at the head of your troops.\r\n')
    ch = readkey ()
    if ch == 'a':
      self.push (Event.travelAlone, (None,))
    if ch == 'p':
      self.push (Event.travelRonin, (None,))
    if ch == 'h':
      self.push (Event.travelTroops, (None,))

  def attackTravelingThieves(self, *args):
    txt = 'Such dogs as these bandits cannot stand before a noble samurai! ' \
          'They break before the ferocity of your attack, and you cut them ' \
          'down as they flee.'
    inc = self.samurai.honor *.25 # gain 25% honor
    if inc < .50: # at least .50
      inc = .50
    if inc > 1: # no more than 1
      inc = 1
    self.push (Event.increaseHonor, (inc,))
    info (txt)

  def encounterThieves(self, *args):
    echo (cls() + '\r\nWhile traveling through the country you encounter ' \
          'a group of thieves who behave in a disrespectful manner. ' \
          'You decide to\r\n')
    echo ('   a: Avoid trouble and go on about your business.')
    echo ('   d: Draw your sword in the defense of honor.')
    ch = readkey ()
    while True:
      if ch == 'a':
        dec = self.samurai.honor * .2 # lose 20% honor
        if dec < .25: # at least .25
          dec = .25
        if dec > 1: # no more than 1
          dec = 1.0
        self.push(Event.decreaseHonor, (dec,))
        return
      elif ch == 'd':
        self.push(Event.attackTravelingThieves, (None,))
        return

  def encounterDrunkenRonin(self):
    echo (cls() + '\r\nYou stop in a village for a cup of sake, but your ' \
          'refreshment is disturbed by a group of drunken ronin ' \
          'who make insolent remarks about your appearance. ' \
          'You decide to\r\n')
    echo ('   a: Avoid trouble and go on abour your business.\r\n')
    echo ('   d: Draw your sword in the defense of honor.\r\n')
    ch = readkey ()
    while True:
      if ch == 'a':
        dec = self.samurai.honor * .2 # lose 20% honor
        if dec < .25: # at least .25
          dec = .25
        if dec > 1: # no more than 1
          dec = 1.0
        if self.samurai.honor -dec < 1: # removing remaining honor
          dec = self.samurai.honor -1
        self.push(Event.dishonorableSeige, (self.samurai,))
        self.push(Event.decreaseHonor, (dec,))
        return
      if ch == 'd':
        self.push(Event.attackTravelingRonin, (None,))
        return

  def encounterTravelingSamurai(self, *args):
    echo (cls() + '\r\nYou encounter a traveling samurai, who says, ' \
          '"I observe that your style of swordsmanship is different from ' \
          'mine. I wish to challenge you to a duel to prove the supiriority ' \
          'of my school."\r\n')
    echo ('   a: Avoid trouble and go on about your business.')
    echo ('   d: Draw your sword in the defense of honor.')
    ch = readkey ()
    while True:
      if ch == 'a':
        dec = self.samurai.honor * .2 # lose 20% honor
        if dec < .25: # at least .25
          dec = .25
        if dec > 1: # no more than 1
          dec = 1.0
        self.push(Event.decreaseHonor, (dec,))
        return
      elif ch == 'd':
        self.push(Event.attackTravelingSamurai, (None,))
        return

  ##
  # Duel / Challenges
  ##

  def acceptedDuel(self, enemy):
    info ('"You cannot so insult my family and live!" %s snarls. ' \
          '"I challenge you to a duel of honor!"' % enemy.name)
    # if won:
    # kill and find heir?
    #self.pushEvent (Event.assumeLeadership, enemy)
    self.push (Event.victoriousDuel, (None,))

  def declinedDuel(self, enemy):
    info ('%s hesitates. He glances at your sword and starts to sweat. ' \
          'Then he smiles nervously and says, "Ah, you are making a ' \
          'little joke. Most amusing." His reainers stare in disbelief; ' \
          'their lord is refusing to avenge a deliberate insult!\n' \
          'Lord %s states, "I am disappointed in %s behavior. %s is ' \
          'a samurai of %s honor.' % \
          (enemy.name, province.hotomoto, enemy.name,
           text.honor[int(enemy.honor)]))

  def challengeEstateDuel(self, enemy):
    " Make a challenge to L{enemy} at his or her estate "
    if random.choice([0,1]):
      # Enemy declines duel
      if enemy.honor >1:
        # enemy honor takes hit
        rmh = enemy.honor *.20 # 20% of current honor
        if rmh <= .25: rmh = .25 # no less than .25
        if enemy.honor -rmh < 1: # remove remaining honor
          rmh = enemy.honor -1
        self.push (Event.decreaseHonor, (rmh,))
      self.push (Event.declinedDuel, (enemy,))
    else:
      # Duel accepted, no honor lost
      self.push (Event.acceptedDuel, (enemy,))

  ##
  # Traveling Events: Estates and Castles
  ##

  def visitSomeone(self, host):
    echo (cls() + '\r\nYou meet %s in a pleasant room overlooking ' \
          'a goldfish pond. You both sit; discreet servants bring ' \
          'food and drink. You tell %s\r\n' % host.name)
    echo ('  c: That he is a coward whos ancestors hauled dung.\r\n')
    echo ('  i: That you wish to invite him to a tea ceremony.\r\n')
    echo ('  g: That you must go\r\n')
    while True:
      ch == readkey()
      if ch == 'c':
        self.push(Event.challengeEstateDuel, (host,))
        return
      if ch == 'i':
        self.push(Event.requestTeaCeremony, (host,))
        return
      if ch == 'g':
        return

  def assinateAtEstate(self, host):
    echo (cls() + '\r\nYou adjust your two swords so they won\'t clank, ' \
          'then slip down the hall, moving from shadow to shadow. You plan ' \
          'a dangerous deed, to assasinate:\r\n')
    if host == self.province.hotomoto:
      echo ('  1: The Most Honorable Lord %s' % host.name)
    else:
      echo ('  1: %s' % host.name)
    info ('Somewhere inside, Lord %s sleeps. You must find his room, ' \
          'slay him, and escape without being identified. If a guard ' \
          'sees you, you must still his tongue by taking his head.')
    info ('You have violated the sacred duty of a retainer to his lord. ' \
          'As an example to others who might contemplate disloyalty, your ' \
          'lord oders your entire family exterminated.')

  def enterCastle(self, lord):
    echo (cls() + '\r\nYou are at the castle of Lord %s. Despite the ' \
          'exquisite gardens and the impeccable manners of the ' \
          'courtiers, you know the castle is a hotbed of intrigue.\r\n' \
          'You decide to\r\n' % lord.name)
    # if a single-man challenge
    #echo ('  a: Announce your readiness to defend the clan\'s honor.')
    # if bride available
    #echo ('  c: Court a bride')
    # if with troops and troop-quest
    #echo ('  b: Tell the Lord your warriors are eager for battle.')
    echo ('  t: travel to somewhere else.\r\n')
    while True:
      ch = readkey()
      if ch == 't':
        self.push(Event.travel (None,))
        return
      elif ch == 'c':
        self.push(Event.courtBride, ('??',))
        return
      elif ch == 'a':
        self.push(Event.handleQuest, ('??',))
        return
      elif ch == 'b':
        self.push(Event.handleQuest, ('??',))
        return

  def enterEstate(self, owner):
    echo (cls() + '\r\nYou are welcomed into the estate of %s.' \
          'The head retainer is polite and correct in his manner, ' \
          'but obviously curious as to why you\'ve come.\r\n' \
          'You tell him you\'d like to\r\n' )
    echo ('  v: Visit someone.\r\n')
    echo ('  l: Leave.\r\n')
    while True:
      ch = readkey()
      if ch == 'v':
        self.push(Event.visitSomeone, (owner))
        return
      if ch == 'l':
        return

  def sneakEstate(self, owner):
    echo (cls() + 'Distracting the guards with a tossed stone, you sneak through ' \
          'the outer gates. Under a willow in the garden, you review your ' \
          'plan.\r\n')
    echo ('   t: Treachery against the lord of this manor.\r\n')
    # has children
    echo ('   h: Take hostage from the lord\'s family.\r\n')
    # is occupied
    echo ('   a: Assasinate someone.\r\n')
    echo ('   l: Leave.\r\n') # like manson!
    #while True:
    #  ch = readkey()

  def arriveEstate(self, owner):
    if owner.name == self.province.hatamoto:
      property = 'castle'
      name = 'Lord %s' % owner.name
    else:
      property = 'estate'
      name = owner.name

    echo (cls() + '\r\nYou arrive at the %s of %s.\r\n' \
          % (property, name))
    echo ('   e: Enter boldly.\r\n')
    # if under guise:
    echo ('   i: Incite the local peasants to rebellion.')
    echo ('   w: wait until nightfall, then sneak past the guards.')
    # if traveling with troops (and not castle?):
    echo ('  o: Order your troops to attack.')
    # if estate is under attack
    echo ('  h: Order your warriors to help %s' % owner.name)
    echo ('   t: Travel somewhere else.\r\n')
    while True:
      ch = readkey()
      if ch == 'e':
        if property == 'castle':
          self.push(Event.enterCastle, owner)
        else:
          self.push(Event.enterEstate, owner)
        return
      elif ch == 't':
        self.push(Event.travel (None,))
        return
      elif ch == 'o':
        self.push(Event.siegeEstate, owner)
        return
      elif ch == 'i':
        self.push(Event.inciteRebellion, owner)
        return
      elif ch == 'w':
        self.push(Event.sneakEstate, owner)
        return

  ##
  # Estate Seiges / Battles
  ##

  def siegeEstate(self, enemy):
    info ('You are committed -- the time for planning is over. ' \
          'Death will come to many today. But you are calm, ' \
          'for only the tranquil mind can be victorious. You ' \
          'array your troops, and give the command to attack.')
    if random.choice([0,1]):
      self.pushEvent (Event.siegedEstate, (enemy,))
    else:
      self.pushEvent (Event.failedEstateSiege, (enemy,))

  def siegedEstate(self, enemy):
    info ('Your victorious troops chase %s soldiers from the field. ' \
          'Such is the fate of all who defy %s!' \
          % (ownership(enemy.name), self.samurai.name))
    dec = self.samurai.honor * .35 # lose 35% honoe
    if dec < .5: # at least .5
      dec = .5
    if dec > 1: # no more than 1
      dec = 1.0
    if self.samurai.honor -dec < 1: # removing remaining honor
      dec = self.samurai.honor -1
    self.pushEvent (Event.dishonorableSeiege, (self.samurai, enemy))
    self.pushEvent (Event.decreaseHonor, (dec,))

  def estateUnderSiege(self, enemy):
    info ('%s of %s has invaded your fief with a %s unit of ' \
          'samurai and claimed your lands for himself. This ' \
          'trespass must not go unchallenged! You announce ' \
          'your eagerness for the coming battle.' \
            % (enemy.name, provinces[enemy.province].clan,
               text.size[int(enemy.warriors)/10]))

  ##
  # Recognition
  ##

  def chkClanRating(self, *args):
    return
    info ('As a result of recent events your standing in ' \
          'the clan has improved. You plan the changes you ' \
          'will make when you become hatamoto!')
    info ('You are now clearly last in your lord\'s favor. ' \
          'Could your rivals have been responsible for this ' \
          'loss of face? Perhaps they need to be taken down ' \
          'a peg or two!')
    info ('Recent events have caused you to fall out of favor. ' \
          'You must work hard to improve your reputation.')
    info ('You are now the clear favorite for the next promotion ' \
          'to hatamoto. Already the poison of jealousy has begun to ' \
          'spread among your rivals.')

  def announceCapture(self, host, enemy):
    txt = '%s was caught at the estate of %s while engaged in some ' \
          'sort of impropriety. %s has been released; it is said that ' \
          'his family paid a small piece of land as a ransom'
    info (txt)

  def announceNewHatamoto(self, hatamoto):
    txt = '%s is proclaimed the new hatamoto. You vow the next time ' \
          'the title will be yours!' % hatamoto.name
    info (txt)

  def dishonorableSeiege(self, samurai, enemy):
    if samurai.handle == handle():
      persons = 'your'
    else:
      persons = ownership(samurai.name)
    info ('Lord %s has ruled that there was no excuse ' \
          'for %s attack on %s. It was a dishonorable ' \
          'act that no faithful retainer would undertake.' \
          % (persons, enemy.name))

  def honorableAct(self, samurai):
    """
    Have the hatamoto describe an honorable action by a samurai as,
    also giving a hint to their level of honor.
    """
    txt = 'Lord %s states, "It is good to see %s perform an honorable act.\n' \
          % (provinces[samurai.province].hatamoto, samurai.name)
    if samurai.honor <3:
      txt += 'However, '
    txt += samurai.name + ' is a ' + text.level[samurai.level].lower() \
      + ' of ' + text.honor[int(samurai.honor)] + ' honor."'
    info (txt)

  def dishonorableAct(self, samurai):
    """
    Have the hatamoto describe a dishonorable action by a samurai,
    also giving a hint to their level of honor.
    """
    samurai = samurais[samuraiName]
    txt = 'Lord %s states, "I am disappointed in %s behavior.\n' \
          % (provinces[samurai.province].hatamoto,
             ownership(samurai.name))
    if samurai.honor <3:
      txt += 'However, '
    txt += samurai.name + ' is a ' + text.level[s.level] \
      + ' of ' + text.honor[int(samurai.honor)] + ' honor."'
    info (txt)


  ##
  # Home Events
  ##

  def practiceKenjutsu(self, *args):
    add = (7 -self.samurai.swordsmanship) * .6
    if add >1: # cap large gains
      add = 1
    elif add < .3: # bump small gains
      add = .3
    if self.samurai.swordsmanship +add > 7: # set tax as maximum value
      add = 7 -self.samurai.swordsmanship
    self.push (Event.increaseSwordsmanship, (add,))
    txt = 'Through diligent practice with your teacher ' \
          'you improve your swordsmanship.'
    info (txt)

  def equipSamurai(self, *args):
    self.samurai.activity = 'Recruiting warriors'
    add = (self.samurai.maxWarriors() -self.samurai.warriors) /3
    if add <= 1: add = 1 # add at least one full body :)
    else: add = int(add)

    self.samurai.set ('warriors', self.samurai.warriors +add)

    if add > 1: plural = '.'
    else: plural = ''
    txt = 'Selecting loyal men of honor and fierceness, you equip %s samurai%s.' \
      % (add, plural)
    info (txt)
    #province.event (Event.increasedSamurai, (self.samurai, add))
    return add

  def samuraiLossByLand(self, samurai, loss):
    " make a note of the loss of warriors due to loss of land "
    if self.handle == handle():
      txt = 'The recent loss of land forces you to release %s %s from ' \
            'your service, as you can no longer afford to maintain them. ' \
            'The warriors become ronin, samurai without a lord.' \
            % (loss, plural('warrior', loss))
    else:
      txt = '%s Recent loss of rice-growing land forces him to release %s ' \
            'samurai from his service, as he can no longer support them ' \
            'properly.' \
            % (samurai.name, loss)
    info (txt)

  def drillTroops(self, *args):
    self.samurai.activity = 'Drilling troops'
    inc = .5
    if self.samurai.generalship+inc> 7.0:
      # make generalship maximum
      inc = 7.0 -self.samurai.generalship
    self.push(Event.increaseGeneralship, (inc,))
    info ('Following the precepts of Sun Tzu\'s Art of War, ' \
          'you drill your troops, sharpening your skills of ' \
          'command and tactics.')

  def raiseTaxes(self, *args):
    self.samurai.activity = 'Taxing the peasants'

    # land aquisition
    add = (7 -self.samurai.land) * .6 #60% of available land
    if add >1: # cap large gains
      add = 1
    elif add < .3: # bump small gains
      add = .3
    if self.samurai.land +add > 7: # set land to maximum value
      add = 7 -self.samurai.land
    self.push (Event.increaseLand, (add,))

    # honor takes hit
    rmh = add *.8 # 80% of land gained becomes honor hit
    if rmh <= .4: rmh = .4 # no less than .4
    if self.samurai.honor -rmh < 1: # removing remaining honor
      rmh = self.samurai.honor -1
    self.push (Event.decreaseHonor, (rmh,))

    info ('You demand a greater percentage of the rice harvest. The peasants ' \
    'grumble, but you deliver a stern message reminding them that it is ' \
    'their duty to obey.')

  def donateLand(self, *args):
    self.samurai.activity = 'Donating land to the Buddhists'
    rm = self.samurai.land /4 # 25% decrease in land
    if rm >1.0: rm = 1.0 # no more than 1
    elif rm < .50: rm = .50 # no less than .50
    if self.samurai.land -rm < 1: # donate remaining land
      rm = self.samurai.land -1
    self.push(Event.decreaseLand, (self.samurai, rm,))

    amh = rm *.8 # 80% of land donated becomes honor
    if amh > 0.5: amh = 0.5 # no more than .50
    if self.samurai.honor +amh > 7.0:
      # make honor maximum
      amh = 7.0 -self.samurai.honor
    self.push(Event.increaseHonor, (amh,))
    info ('You donate some of your finest rice-growing land to the ' \
          'service of the Buddhas.')

  ##
  # Home
  ##

  def home(self, *args):
    self.samurai.activity = 'Considering a course of action'
    echo (cls() + '\r\nConsidering the situation, you decide to\r\n')
    if self.samurai.warriors < self.samurai.maxWarriors():
      echo ('   e: equip more samurai.\r\n')
    if self.samurai.swordsmanship < 7.0:
      echo ('   p: practice kenjutsu.\r\n')
    if self.samurai.generalship < 7.0:
      echo ('   d: drill your troops.\r\n')
    if self.samurai.land > 1.0:
      echo ('   l: donate land to the local Buddhist temple.\r\n')
    if self.samurai.land < 7.0:
      echo ('   r: raise the rice tax within your domain.\r\n')
    echo ('   q: quit for the day.\r\n')
    echo ('   t: travel.\r\n')
    ch = readkey ()
    if ch == 'q':
      self.push (Event.quit, (None,))
      return
    if ch == 'e':
      self.push (Event.equipSamurai, (None,))
      return
    if ch == 'r':
      self.push (Event.raiseTaxes, (None,))
      return
    if ch == 'l':
      self.push (Event.donateLand, (None,))
      return
    if ch == 'p':
      self.push (Event.practiceKenjutsu, (None,))
      return
    if ch == 'd':
      self.push (Event.drillTroops, (None,))
      return

  ##
  # Quit
  ##

  def quit(self, *args):
    echo ('you is quitting PAK, args: %s\n\n' % repr(args))
    readkey ()
    return None

  ##
  # Player creation
  ##

  def joinProvince(self, provinceName):
    " join a province, generating ai if necessary "

    # add self as member of province
    self.samurai.joinProvince (provinceName)

    # update our reference to province
    self.province = provinces[self.samurai.province]

    # ensure hatamoto exists in province
    self.province.chkCreateHatamoto ()

    # ensure minimum number of samurais exist in province
    self.province.chkCreateSamurais ()

    # bump other samurai AI's until we are the lowest ranked
    self.province.makeLowestRank (self.samurai)

    self.push (Event.welcomeProvince, (self.province,))

  def describeProvinceSamurais(self, province):
    " describe the competition "
    ranked_vassals = province.getMembers()
    for n, vassal in enumerate(ranked_vassals):
      info (samurais[vassal].print_rankDescription())


  def welcomeProvince(self, province):
    " display welcoming message "
    print 'ARGS', province, type(province)
    info ('Lord %s, the hatamoto whom you will serve, welcomes you into ' \
          'the ranks of his samurai subordinates. He says, "Your father ' \
          'served %s clan well - I am sure you will live up to his name. ' \
          'Please be introduced to my other samurai." Each rival inspects ' \
          'you closely as you meet him.' \
          % (province.hatamoto, province.clan))
    self.push (Event.describeProvinceSamurais, (province,))

  def joinGame(self, handle):
    """
    Join the game using a previously created character.
    """
    if not samuraiExist(handle):
      self.push(Event.newSamurai, (handle,))
      return
    self.samurai = samurais[handle]
    self.province = provinces[self.samurai.province]
    info ('Welcome back!')

  def newSamurai(self, handle):
    def select_advantage():
        echo (color() + cls() \
            + pos(center(text.advantage), 8) + text.advantage
            + pos(center(text.advantagehint), 22) + text.advantagehint)
        wt, ht = (maxwidth(text.attributes)+2)*' ', len(text.attributes)+2
        adv = lightclass(ansiwin(y=12,x=center(wt), h=ht, w=len(wt)))
        adv.alignment = 'center'
        adv.ans.lowlight (partial=True)
        adv.update (text.attributes)
        return adv.run ()

    def select_province():
      echo (cls() + color() + \
            pos(center(text.provselect), 2) + \
            text.provselect)

      # build provinces lightbar and province info window
      provinceNames = provinces.keys ()
      provwidth = maxwidth(provinceNames)+2
      provbar = lightclass(ansiwin(y=4,x=7,h=20,w=provwidth))
      provbar.interactive, provbar.alignment = True, 'center'
      provbar.ans.partial = True
      provbar.ans.lowlight ()
      provbar.update (provinceNames)

      # build province info pager
      provpager = paraclass(ansiwin(y=4, x=provbar.ans.x+provbar.ans.w+7,h=20,w=80-(7+provwidth+14)), xpad=3, ypad=2, split=8)

      # select a province
      while True:
        if provbar.moved:
          provpager.ans.lowlight (partial=True)
          provpager.update (provinces[provbar.selection].print_details(), align='top')
          provpager.ans.title ('-< ' + provbar.selection + ' >-')
          provpager.ans.title ('-< return:select province >-< +/-:scroll >-', align='bottom')
          provpager.refresh ()
        provbar.run ()
        if provbar.exit: return None
        if provbar.lastkey == '-': provpager.up ()
        if provbar.lastkey == '+': provpager.down ()
        if provbar.lastkey == KEY.ENTER: return provbar.selection

    def select_name(max_name=12):
      while True:
        echo (cls() + color() + color(CYAN))
        n = 8
        # display name prompt centered seperated by a blank line
        for row, line in enumerate(text.nameprompt):
          echo (pos(center(line), row +n) + line)
          n +=1
        n += 2
        echo (pos(center(text.namehint), 22) + text.namehint\
            + pos(80/2 +max_name/2 +1, row +n) + ']' \
            + pos(80/2 -max_name/2 -2, row +n) + '[ ' \
            + cursor_show() + color(*WHITE))
        name = readline(max_name)
        echo (cursor_hide())
        if samuraiExist(name):
          echo (color(*YELLOW) + \
                pos(center(text.nametaken), 22) + \
                text.nametaken)
          readkey ()
          continue
        return name

    name = select_name()
    if not name:
      return False

    # create samurai
    self.samurai = Samurai (handle) # record key is user handle
    self.samurai.set('name', name) # chosen samurai name
    self.samurai.set('ai', False)  # non-ai
    self.samurai.set('level', 1) # lowest level
    self.samurai.set('age', 1) # a young strappling
    self.samurai.set('aggression', 0)
    self.samurai.set('warriors', 0)
    selectedProvince = select_province ()
    if not selectedProvince:
      return False
    self.samurai.set('province', selectedProvince)

    adv = select_advantage ()
    # copy province attributes
    for key in ['honor','generalship','swordsmanship','land']:
      self.samurai.set (key, provinces[self.samurai.province][key])

    # set family advantage
    self.samurai.set (adv, self.samurai[adv] +1)

    # add samurai to database
    self.samurai.save ()

    # equip samurai
    self.push (Event.equipSamurai, (),)

    # join province
    self.push (Event.joinProvince, (self.samurai.province,))
    return True
