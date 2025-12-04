global animals
global cypher
from entities import *
import random
animals = {'Shark':10,'Cat':15,'Lion':12,'Dog':17,'Snake':14,'Mouse':19}
class AnimalChart(Item):
  def __init__(self,name='Animal Chart'):
    super().__init__(name)

  def get_description(self) -> str:
    return 'There is a chart on the wall with animals and numbers.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.read(),'Read animal chart.'))
    return options

  def read(self):
    message = 'The chart has a list of animals and numbers.'
    for animal in animals.keys():
      message += f'''\n| {animal!s:5} = {str(animals[animal]) if animal != 'Mouse' else '??'!s} |'''

    self.send_message(message)

letters = []
for code in range(ord('A'),ord('Z')+1):
  letters.append(chr(code))

letters.reverse()
letters_shuffled = letters.copy()
random.shuffle(letters_shuffled)
cypher = {}
while len(letters) > 0:
  cypher[letters.pop()] = letters_shuffled.pop()

class CryptoCypherCard(Item):
  def __init__(self,name='Crypto Cypher Card'):
    super().__init__(name)

  def get_description(self) -> str:
    return 'A card with a cryptography cypher'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.read(),'Read cypher card.'))
    return options

  def read(self):
    message = 'Cypher:'
    cypher_keys = list(cypher.keys())
    for row_num in range(0,6):
      line = '|'
      for col_num in range(0,5):
        key_num = row_num*5+col_num
        if key_num < len(cypher_keys):
          line += f''' {cypher[cypher_keys[key_num]]!s}={cypher_keys[key_num]!s} '''
          continue

        line += '     '

      line += '|\n'
      message += line

    self.send_message(message)

class Computer(Item):
  def __init__(self,name='Computer'):
    super().__init__(name)
    self.checked = False
    self.password = 'logical'
    self.note = ''
    for ch in self.password:
      self.note += cypher[ch.upper()]

  def get_description(self) -> str:
    return 'There is a computer on a desk.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.check(),'Check out computer.'))
    if self.checked and self.world.rooms['Breakroom'].central_left_unlocked:
      options.append((lambda : self.enter_password(),'Enter password on computer.'))

    return options

  def check(self):
    self.checked = True
    self.send_message('''The computer looks like it\'s asking for a password.
There is a cryptic note taped to the corner of the monitor that says:
 --- That is so '''+self.note)

  def enter_password(self):
    if self.ask('Please enter password').lower() == self.password:
      self.world.rooms['Breakroom'].central_left_unlocked = True
      self.send_message('''Password Accepted!  Brilliant work!

<A LOUD CHIME COMES FROM THE BREAKROOM>''')
      return None
    else:
      self.send_message('Incorrect password!  Try again.')
      return None

class Safe(Item):
  def __init__(self,name='Safe'):
    super().__init__(name)
    self.unlocked = False
    self.n1 = animals['Cat']
    self.n2 = animals['Dog']
    self.n3 = animals['Mouse']

  def get_description(self) -> str:
    return 'A small safe is on a table.  It has a 3 number dial lock.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.unlocked:
      options.append((lambda : self.unlock(),'Try to unlock the safe.'))

    return options

  def unlock(self):
    self.send_message('The safe has a dial lock.  You will need to turn the lock right to the 1st number,\nleft to the 2nd number, and then right to the 3rd number.')
    n1_attempt = self.ask_number('1st - Turn right to (2 digit number)',2)
    n2_attempt = self.ask_number('2nd - Turn left to (2 digit number)',2)
    n3_attempt = self.ask_number('3rd - Turn right to (2 digit number)',2)
    if n1_attempt == self.n1 and n2_attempt == self.n2 and n3_attempt == self.n3:
      self.unlocked = True
      self.send_message('You hear a click and the safe opens!\nInside is a card with a cryptography cypher.')
      CryptoCypherCard().set_parent(self.world.player)
      return None
    else:
      self.send_message('You try to open the safe and it\'s still locked.')
      return None

class Left(Room):
  def __init__(self,name='Left'):
    super().__init__(name)
    AnimalChart().set_parent(self)
    Safe().set_parent(self)
    Computer().set_parent(self)

  def get_description(self) -> str:
    desc = '$div'
    desc += 'You are in the Left Wing.  Math symbols and diagrams adorn the walls.  You feel smart being here.'
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