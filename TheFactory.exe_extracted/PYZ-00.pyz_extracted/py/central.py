global photo_width
global photo_height
global photo_chars
global card_width
global card_height
global card_front_str
global card_back_str
import random
from entities import *
from breakroom import Photo
photo_str = '''████████████████████████████████████████████████████████████████████████████████
██                                                                            ██
██                                           ,▄▓▓▓▓▓▓▓▓▄▄,                    ██
██                                         ╓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▄                 ██
██                                       .▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▄               ██
██                                       ║▓▓▌└\'\'└╙╙╙▀▀▀▀▀▀\'╙▓▓▓               ██
██                                       ║▓▓▌╓▄▄▓▓\'\'\'\'▓▓▄▄▄ƒ▓▓▓               ██
██                                        ▓▓└└,;,\'\'\'\'\'\'┌,;.\'╫▓▌               ██
██            ╓▄▓▓▓▓▓▓▓▓▓▓▌,              ╟▌\'▐.▓▒`\'\'\'\'\'▓▒µ╙\'▐▓┌               ██
██          ▄▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓,          .]╠.\'.╙┤-\'\'¡\'░│╙┌ \'╚▒.               ██
██         ▓▓▓▓▓▓▓▓▓▓▓▓▓▌└▓▓▓▓▓            \'\'\'\'\'\',:::::\'\'\'\'.\'\'                ██
██        ]▓▓▓▓▓▓▓▓▓▀╬╣╙┌,╚▓▓▓▓▌             \'\'\'\'▓▓▓▄▓▓▒\'\'\'                   ██
██        ╫▓▓▌╝▀▀▀Γ\'└ \'╙╙╙╙╙▓▓▓▓              \'┌\' ╙╙╙╙┘\'┌\'                    ██
██        ▓▓▓▒╓Mj░∩\'\'\'\'=Q▄7▒▐▓▓▓                ²ε;,,;;φ                      ██
██       ]▌╙▓▌╙ ▓▀ ┌,\'\' ▀▓ └▐▓▒▐L            ╓▄⌐ \':\'└└:  ╠▓▄µ                 ██
██       ▓▓µ▓▓\':░░┌.\':\'.░░\'\'▐▓▒▓▌       ,▄▓▓███▌. 4██▓⌐ -▓█████▓▌▄╖           ██
██      ▐▓▓▓▓▓▄\'\'^▓▓▓▓▓▓▀\'\']▓▓▓▓▓⌐  ▄▄▓████████▓▌` ╟█▌  ╣▓███████████▌        ██
██      ╟▓▓▓▓▓█▓▄.\'╙╙╙╙└\',▄██▓▓▓▓⌐]█████████████▓▒ ╫█▌ å▓▓████████████▌       ██
██     «╣▓▓▓██████▌≥ε;≤∩╟█████▓▓▓▌▓█████████████▓▓▄▓██╔▓▓██████████████       ██
██     ]▓▓▓▓█████▓▀\'\'\'\'\'┘╙▀▀██▓▓▓▓████████████▓█▓▓▓▓██▓▓▓██████████████µ      ██
██      ╚▀▓▀▀╠╬╬▒⌐\'\'\'\'\'\'\'\':╠╬╬╠⌐└╫███████████████▓▓▓▓▓▓▓▓██████████████▓      ██
██        .\'\'╠╬╬╬╠∩.\'\'\'\'\'┌╠╬╬╬╬░:▓███████████████▓▓▓▓▓▓▓▓███████████████      ██
██        \'\'\'╠╬╬╬╬╬▒;\'\'\';╠╬╬╬╬╬▒]█████████████████▓▓▓▓▓▓▓███████████████▌     ██
██        \'\'\'╠╬╬╬╬╬╬╟╦;φ╠╬╬╬╬╬╬╠╟█████████████████▓▓▓▓▓▓████████████████▌     ██
██       :\'\'┌╠╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬╠▓██████▌╫█████████▓▓▓╣▓▓█████████████████     ██
██       \'\'\'\':╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬░██▓╩┘\'\'\'\'╙█████████▓▓▓▓▓██████████╙██████     ██
██      .\'\'\':  ╬╬╬╬╬╬╬╬╬╬╬╬╬╬╬▒]█╩,ô;µ┌\',▓█████████▓▓╬▓▓▓█████████ ██████L    ██
██      \'\'\'\'   ╚╬╬╬╬╬╬╬╬╬╬╬╠╠╬Γ ║▒▄Θ▒φ╓▄████████▓▀╙└\'^:::╙████████ ▓█████▌    ██
██     :\'\'\'\'    ╬╬╬╬╬╬╬╬╬╠╠╠╬╬▒  └╨▀▀▓██████████⌐\'\'\'\'\'┌;;¡▓███████ ║█████▌    ██
██    ┌\'\'\':    ,╬╬╬╬╬╬╬╠╠╠╬╬╬╬╟         ╙███████,▄;\'\'\'ⁿ⌐;▓████████ └█████▌    ██
██   ┌\'\'.\'     ╟╬╬╬╬╬╠╬╬╬╬╬╬╬╬╬╬         █████████▓▓▓▓▓▓██████████⌐ █████▌    ██
████████████████████████████████████████████████████████████████████████████████'''
photo_width = len(photo_str.split('\n')[0])+1
photo_height = len(photo_str.split('\n'))
photo_chars = list(photo_str)
card_width = int(photo_width-1/5)
card_height = int(photo_height/4)
card_front_str = '''┌──────────────┐
│              │
│              │
│              │
│              │
│              │
│              │
└──────────────┘'''
card_back_str = '''╔══════════════╗
║ █▓▒░░░░░░▒▓█ ║
║ ▓▀        ▀▓ ║
║ ░          ░ ║
║ ░          ░ ║
║ ▓▄        ▄▓ ║
║ █▓▒░░░░░░▒▓█ ║
╚══════════════╝'''
class Machine(Item):
  def __init__(self,name='Machine'):
    super().__init__(name)
    self.checked = False
    self.cards = []

  def get_description(self) -> str:
    return 'The only thing in the room is a machine.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.world.rooms['Lobby'].is_opened:
      options.append((lambda : self.check(),'Check out the machine.'))
      if self.checked:
        if self.get_child_by_type(Photo) is None and self.world.player.get_child_by_type(Photo) is not None:
          options.append((lambda : self.start(),'Insert photo into machine.'))
        else:
          options.append((lambda : self.find_match(),'Try to find a match.'))

    return options

  def setup(self):
    for face in (self.world.name,self.world.player.name,'Mom','Dad','Hank','Barbara','Chuck','Emily','Creativity','Intelligence'):
      for num in range(2):
        self.cards.append({'face':face,'found':False})

    random.shuffle(self.cards)

  def check(self):
    self.checked = True
    self.send_message('''The machine has a panel with a grid of buttons with numbers.  Above the panel is a screen.
Next to the screen is a slot and a message saying:
 --- Insert photo to begin.''')

  def start(self):
    photo = self.world.player.get_child_by_type(Photo)
    photo.set_parent(self)
    self.setup()
    self.send_message('''You insert the photo into the machine.  The buttons on the panel light up.
The screen turns on and displays a set of cards. and the message:
 --- Find all of the matches''')

  def screen_new(self) -> list[str]:
    return photo_chars.copy()

  def screen_set(self,screen: list[str],x: int,y: int,s: str):
    y_offset = 0
    for line in s.split('\n'):
      x_offset = 0
      for ch in line:
        screen[y+y_offset*photo_width+x+x_offset] = ch
        x_offset += 1

      y_offset += 1

  def draw_card(self,screen: list[str],card_num: int,found: bool = False):
    card = self.cards[card_num]
    row_num = card_num//5
    col_num = card_num%5
    if card['found'] and found:
      self.screen_set(screen,col_num*card_width,row_num*card_height,card_back_str)
      x = col_num*card_width+card_width//2-1
      y = row_num*card_height+card_height//2-1
      self.screen_set(screen,x,y,str(card_num+1))
      return None
    else:
      self.screen_set(screen,col_num*card_width,row_num*card_height,card_front_str)
      x = col_num*card_width+card_width//2-1
      y = row_num*card_height+card_height//2-1
      face = ''
      face_lines = card['face'].replace(' ','\n').split('\n')
      y -= len(face_lines)//2
      face_line_length = 0
      for face_line in face_lines:
        face += face_line+'\n'
        if len(face_line) > face_line_length:
          face_line_length = len(face_line)

      x -= face_line_length//2
      self.screen_set(screen,x,y,face)
      return None

  def find_match(self):
    screen = self.screen_new()
    for row_num in range(4):
      for col_num in range(5):
        card_num = row_num*5+col_num
        card = self.cards[card_num]
        if card['found']:
          self.draw_card(screen,card_num)

    prompt = '''The screen shows 20 cards that match up to the 20 cards that match the 20 buttons
on the panel.
'''
    prompt += ''.join(screen)+'\n'
    prompt += 'You are looking for a match.\nWhat is your first card?'
    options = []
    for card_num,card in enumerate(self.cards):
      if card['found']:
        options.append(str(card_num+1))

    c1 = int(self.ask(prompt,options))-1
    self.draw_card(screen,c1,True)
    options.remove(str(c1+1))
    prompt = ''.join(screen)+'\nWhere is the other '+self.cards[c1]['face']+'?'
    c2 = int(self.ask(prompt,options))-1
    self.draw_card(screen,c2,True)
    self.send_message(''.join(screen))
    card1 = self.cards[c1]
    card2 = self.cards[c2]
    if card1['face'] == card2['face']:
      card1['found'] = True
      card2['found'] = True
      self.send_message('You found a match!')
      num_not_found = 0
      for card in self.cards:
        if card['found']:
          num_not_found += 1

      if num_not_found == 0:
        self.world.rooms['Lobby'].is_opened = True
        photo = self.get_child_by_type(Photo)
        photo.blurred = False
        photo.set_parent(self.world.player)
        screen = self.screen_new()
        self.send_message(''.join(screen)+'''
You can\'t believe your eyes!  It\'s...your Mom and Dad.
The machine returns the photo to you.

You hear gears turning in the distance back in the direction of the
lobby.

<YOU CLEARLY HEAR A DOOR OPEN AND THE FEELING OF FRESH AIR RUSH IN>''')
        return None
      else:
        return None

    else:
      self.send_message('They didn\'t match.  Try again.')
      return None

class Central(Room):
  def __init__(self,name='Central'):
    super().__init__(name)
    self.checked = False
    Machine().set_parent(self)

  def get_description(self) -> str:
    desc = '$div'
    desc += 'You are in the Central room.  The room is large and very quiet.\n'
    for child in self.children:
      if child.get_visible() and child.is_a('Player'):
        child_desc = child.get_description()
        if len(child_desc) > 0:
          desc += '\n'+child_desc

    desc += '''
There is a door behind you leading back to the breakroom.
'''
    return desc

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = super().get_options()
    options.append(('B','Go back to the breakroom.'))
    return options

  def handle_option_answer(self,value: str):
    if value == 'B':
      self.send_message('You head back to the breakroom.')
      self.world.player.set_parent(self.world.rooms['Breakroom'])
      return None
    else:
      return None