"""
Game text for Sword of the Samurai.
"""
__author__ = ''
__version__ = '$Id'
__copyright__ = ''
__license__ = ''

# calculated game text
defaultGameText = {
  'pause': [
    'Contemplate the virtue of patience...',
    'Endure delays with fortitude...',
    'To wait calmly requires discipline...',
    'Suspend expectations of imminence...',
    'The tide hastens for no man...',
    'Cultivate a stoic calmness...',
    'The tranquil mind eschews impatience...',
    'Deliberation is preferable to haste...' ],
  'nameprompt': [
    'Samurai warrior,', 'please announce the name',
    'by which you wish to be known:' ],
  'namehint': 'Type name, then press Return',
  'nametaken': 'A samurai warrior already goes by such name',
  'provselect': 'Select a province',
  'advantage': 'Family advantage',
  'advantagehint': 'Make selection and press enter',
  'attributes': ['swordsmanship', 'generalship', 'honor', 'land'],
  'honor': [
    '(null)'
    'very little', 'little', 'barely adequate', 'satisfactory', 'commendable',
    'great', 'extreme', 'unsurpassed',
    'XXX','ZZZ'],
  'size': [
    '(null)',
    'tiny', 'very small', 'small', 'moderate', 'large', 'very large', 'vast',
    'PPP','QQQ'],
  'bigness': [
    '(null)',
    'is a disappointment.',
    'is an adequate retainer.',
    'has many fine qualities.',
    'is the most capable.'],
  'age': [
    '(null)',
    'Child', 'Youth', 'Young Adult', 'Mature Adult', 'Aged'],
  'aggression': [
    '(null)', 'Cautious', 'Aggressive'],
  'aggrivation': [
    'Mildly', 'Moderately', 'Intensely'],
  'level': [
    '(null)', 'Samurai', 'Hatamoto', 'Daimyo'],
  'activities': [
    'Whereabouts unknown',
    'On way to bold deeds',
    'Equipping his troops',
    'On way to campaign',
    'Helping to defend ',
    'Courting the daughter of ',
    'Committing treachery against ',
    'Attacking ',
    'Issuing a challenge to ',
    'Kenjutsu practice',
    'Kidnap a relative of ',
    'Rescuing a family member from ',
    'Inciting the peasants of ',
    'Committing seppuku',
    'Tithing part of his land',
    'Taxing the peasants',
    'Assassinating ',
    'Considering a course of action',
    'Travelling',
    'Drilling his troops',
    'Choosing retirement',
    'Offering a tea ceremony to ',
    'Considering conquest',
    'Defending his fief'],
  'location': [
    'On the road',
    'At your estate',
    'At his estate',
    '\'s estate',
    ', with army'],
  'deed': 'Bold Deeds Available',
  'deeds': [
    'None at this time',
    'Bandits are robbing villages near the lord\'s castle.',
    'At your lord\'s castle, a swordsman craves a duel.',
    'Peasants near your lord\'s castle hold a hostage.',
    'Ronin are menacing travelers near the lord\'s castle.',
    'An assassin has been cornered in your lord\'s castle.'],
  'campagin': 'Campaign Action Available',
  'campagins': [
    'None at this time',
    'The lord would like an enemy castle taken.',
    'The lord wants the enemy cleared from the pass.',
    'The lord wants the enemy invasion force destroyed.',
    'Your lord wants the warrior-monks army defeated.'],
  'provinces': [
    'Satsuma', 'Hizen', 'Higo', 'Hyuga', 'Chikuzen', 'Bungo', 'Tosa', 'Sanuki',
    'Nagato', 'Suwo', 'Iwami', 'Izumo', 'Bingo', 'Hoki', 'Bitchu', 'Mimasaka',
    'Bizen', 'Inaba', 'Harima', 'Tango', 'Tamba', 'Settsu', 'Izumi', 'Yamato',
    'Echizen', 'Mino', 'Mikawa', 'Kaga', 'Hida', 'Etchu', 'Shinano', 'Totomi',
    'Suruga', 'Sagami', 'Echigo', 'Kozuke', 'Musashi', 'Shimosa', 'Hitachi',
    'Mutsu', 'Dewa'],
  'sea': [
    'East China Sea', 'Pacific Ocean', 'Sea of Japan', 'Inland Sea'],
  'clanname': [
    'Shimazu', 'Ryuzoji', 'Takahashi', 'Hosokawa', 'Otomo', 'Todo', 'Chosokabe',
    'Hachisuka', 'Naito', 'Ouchi', 'Toida', 'Mori', 'Amako', 'Kobayakawa',
    'Kikkawa', 'Matsuya', 'Tsuyama', 'Ukita', 'Yamana', 'Ikeda', 'Ishiki',
    'Hatano', 'Toyotomi', 'Miyoshi', 'Horiuchi', 'Tsutsui', 'Asai', 'Kitabatake',
    'Asakura', 'Tokugawa', 'Niwa', 'Ishikawa', 'Jinbo', 'Murakami', 'Imagawa',
    'Nakamura', 'Kasigi', 'Takeda', 'Hojo', 'Uesugi', 'Asano', 'Miyagi', 'Satomi',
    'Satake', 'Date', 'Mogami'],
  'familyname': [
    'Akahito', 'Akifusa', 'Anteki', 'Arihito', 'Asakari', 'Bukahito', 'Bukiyo',
    'Buntaro', 'Chizaemon', 'Chomei', 'Choon', 'Chuemon', 'Chuzobo', 'Daigaku',
    'Daigoro', 'Denko', 'Doken', 'Doko', 'Eigen', 'Eijun', 'Eisei', 'Fuhito',
    'Fusayuki', 'Fusazaemon', 'Geki', 'Genzaemon', 'Gohei', 'Gorozaemon',
    'Genbei', 'Harukata', 'Harunobu', 'Hideo', 'Hironori', 'Hirooki', 'Hirotaka',
    'Hiroteru', 'Hiroyasu', 'Ichian', 'Ichiyuken', 'Iesada', 'Ieyasu', 'Inosuke',
    'Jibusaemon', 'Jinbei', 'Jinku', 'Jokyu', 'Junkei', 'Kansuke', 'Kichibei',
    'Kinbei', 'Kiyoji', 'Kiyomasa', 'Kiyosuke', 'Kuemon', 'Masanori', 'Masasaki',
    'Masato', 'Mitsune', 'Motoharu', 'Munesada', 'Nagachika', 'Nagamasa',
    'Nakano', 'Naohiro', 'Nobukimi', 'Okifusa', 'Okiyuki', 'Oribei', 'Oshikatsu',
    'Osoroshi', 'Riemon', 'Rihei', 'Rokubei', 'Ryotetsu', 'Sadaie', 'Sadamura',
    'Sakuan', 'Shoun', 'Sozo', 'Sumimoto', 'Tadahiro', 'Takanobu', 'Takeaki',
    'Takehisa', 'Tamenaka', 'Terumasa', 'Terutora', 'Tomonori', 'Toshiro',
    'Toyoaki', 'Ujikiyo', 'Ujinoro', 'Ukyo', 'Umakai', 'Ungo', 'Yasuhira',
    'Yasuyori', 'Yoichi', 'Yoshiaki', 'Yukihira', 'Yukinaga', 'Yukinari',
    'Yukio', 'Zatoichi'],
  'name': [
    'Abutsu', 'Hamada', 'Haru', 'Haruko', 'Inoe', 'Iratsume', 'Ishihime',
    'Juteini', 'Kazuko', 'Kiku', 'Kishi', 'Kitashi', 'Mariko', 'Matsukaze',
    'Miruku', 'Momo', 'Murasame', 'Seishi', 'Take', 'Tamamo', 'Tokiwa',
    'Tomoe', 'Toshi', 'Yoko', 'Yuki'],
}
