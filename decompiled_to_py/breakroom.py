from entities import *
from giftshop import Dollar
class ClockInOutBoard(Item):
  def __init__(self,name='Clock In or Out'):
    super().__init__(name)
    self.clocked_in_checked = False
    self.clock_in_num = 0
    self.clock_in_order = ['Hank Little','Barbara James','Chuck Huitt','Emily Johnson']
    self.clocked_in = {'Emily Johnson':False,'Chuck Huitt':False,'Hank Little':False,'Barbara James':False}

  def get_description(self) -> str:
    pass
    return 'A board to clock employees in or out is on the wall.  There is a\nlight and a toggle switch next to each employee\'s name.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.status(),'Who is clocked in or out?'))
    if self.clocked_in_checked and self.world.rooms['Breakroom'].left_unlocked:
      options.append((lambda : self.clock_in(),'Clock someone in.'))

    return options

  def status(self):
    self.clocked_in_checked = True
    message = 'You look at the board and can see that:'
    for employee in self.clocked_in.keys():
      message += '\n -- '+employee+' is clocked '+'in' if self.clocked_in[employee] else 'out'

    self.send_message(message)

  def clock_in(self):
    options = []
    for employee in self.clocked_in.keys():
      if self.clocked_in[employee]:
        options.append((employee,'Clock in %s'%employee+'.'))

    employee = self.ask_option('Who would you like to clock in?',options,False)
    if self.clock_in_order[self.clock_in_num] == employee:
      self.clocked_in[employee] = True
      self.clock_in_num += 1
      self.send_message('You flip the switch and clock in %s'%employee)
      if self.clock_in_num >= len(self.clock_in_order):
        self.world.rooms['Breakroom'].left_unlocked = True
        self.send_message('\n<YOU HEAR LOUD CLICK TO THE LEFT>')
        return None
      else:
        return None

    else:
      for employee in self.clocked_in.keys():
        self.clocked_in[employee] = False

      message = 'You try to flip the switch, but it just throws a spark and flips back.'
      if self.clock_in_num > 0:
        message += '\nIn fact, it has flipped all of the switches back.  Everyone is clocked out.'

      self.clock_in_num = 0
      self.send_message(message)
      return None

class Key(Item):
  def __init__(self,name='Key'):
    super().__init__(name)

  def get_description(self) -> str:
    return 'Silver key with an R on it.'

class VendingMachine(Item):
  def __init__(self,name='Vending Machine'):
    super().__init__(name)
    self.checked = False

  def get_description(self) -> str:
    return 'A vending machine is in the corner.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.world.rooms['Breakroom'].right_unlocked and self.world.player.get_child_by_type(Key) is None:
      if self.checked:
        options.append((lambda : self.use(),'Check the vending machine.'))
      else:
        options.append((lambda : self.use(),'Use the vending machine.'))

    return options

  def use(self):
    if self.checked:
      self.checked = True
      self.send_message('It looks like a regular old vending machine.  It has a key pad for letters and numbers,\nbut the glass is scratched and dirty so you can\'t see what\'s in the machine to get.')
      return None
    else:
      dollar = self.world.player.get_child_by_type(Dollar)
      if dollar is not None:
        self.send_message('You insert the dollar in to the vending machine.  Now you need to pick something.')
        letter = self.ask_option('Pick a letter',[('A','A'),('B','B'),('C','C'),('D','D'),('E','E'),('F','F')],False)
        number = self.ask_option('Pick a number',[('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6')],False)
        if letter == 'E' and number == '5':
          self.world.player.remove_child(dollar)
          Key().set_parent(self.world.player)
          self.send_message('You hear cranks turning and then something metalic drop down.\nIt\'s a key.  You take the key.')
          return None
        else:
          self.send_message('You hear a buzz and it returns your dollar.')
          return None

      else:
        self.send_message('You press the buttons but nothing happens.  Maybe you need some money?')
        return None

class Photo(Item):
  def __init__(self,name='Photo'):
    super().__init__(name)
    self.blurred = True

  def get_description(self) -> str:
    if self.blurred:
      pass
      return 'It\'s a photo of a man and woman.  Their faces are blurry and you can\'t quite\nmake out who they are.'
    else:
      pass
      return 'It\'s a picture of your parents.  On the back it says:\n --- Remember'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    return options

class Jacket(Item):
  def __init__(self,name='Jacket'):
    super().__init__(name)
    self.on = False

  def get_description(self) -> str:
    return 'Warm flannel jacket.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.on:
      options.append((lambda : self.take_off(),'Take the jacket off.'))
      if self.world.player.get_child_by_type(Photo) is None:
        options.append((lambda : self.check_pocket(),'Check the jacket pocket.'))

    else:
      options.append((lambda : self.put_on(),'Put the jacket on.'))

    return options

  def put_on(self):
    message = 'You put the jacket on.  It\'s nice and warm.'
    if self.world.player.get_child_by_type(Photo) is None:
      message = '\nThe jacket has a pocket on the side.'

    self.on = True
    self.send_message(message)

  def take_off(self):
    self.on = False
    self.send_message('You take the jacket off.')

  def check_pocket(self):
    Photo().set_parent(self.world.player)
    self.send_message('You check the jacket pocket and find a photo.')

class Breakroom(Room):
  def __init__(self,name='Breakroom'):
    super().__init__(name)
    self.left_unlocked = False
    self.right_unlocked = False
    self.right_checked = False
    self.central_left_unlocked = False
    self.central_right_unlocked = False
    ClockInOutBoard().set_parent(self)
    VendingMachine().set_parent(self)

  def get_description(self) -> str:
    desc = '$div'
    desc += 'You are in the $room.  There are a bunch of dusty tables and chairs.'
    if self.world.player.get_child_by_type(Jacket) is None:
      desc += '\nThere is a flannel jacket on the back of one of the chairs.'

    for child in self.children:
      if child.get_visible() and child.is_a('Player'):
        child_desc = child.get_description()
        if len(child_desc) > 0:
          desc += '\n'+child_desc

    desc += '''
There are doors to the left and to the right.
'''
    desc += '\nThere is also a door in the center of the back wall.  '
    if self.central_left_unlocked and self.central_right_unlocked:
      desc += 'The center door has 2 green check on it.'
    else:
      desc += 'The center door has 1 red X\'s and 1 green check on it.'
      desc += __CHAOS_PY_NULL_PTR_VALUE_ERR__ if self.central_right_unlocked else __CHAOS_PY_NULL_PTR_VALUE_ERR__ if self.central_left_unlocked else 'The center door has 2 red X\'s on it.'

    return desc

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = super().get_options()
    options.append(('B','Go back through the door to the Lobby.'))
    options.append(('L','Go through the left door.'))
    if self.right_checked and self.world.player.get_child_by_type(Key) is not None:
      options.append(('R','Unlock right door.'))
    else:
      options.append(('R','Go through the right door.'))

    options.append(('C','Go through the center door.'))
    if self.world.player.get_child_by_type(Jacket) is None:
      options.append(('J','Take the jacket.'))

    return options

  def handle_option_answer(self,value: str):
    match value:
      case 'B':
        self.send_message('You head back to the Lobby.')
        self.world.player.set_parent(self.world.rooms['Lobby'])
        return None
      case 'L':
        if self.left_unlocked:
          self.send_message('You go through the left door.')
          self.world.player.set_parent(self.world.rooms['Left'])
          return None
        else:
          self.send_message('You try the left door, but it is locked.')
          return None

      case 'R':
        if self.right_unlocked:
          self.send_message('You go through the right door.')
          self.world.player.set_parent(self.world.rooms['Right'])
          return None
        else:
          key = self.world.player.get_child_by_type(Key)
          if self.right_checked and key is not None:
            self.world.player.remove_child(key)
            self.right_unlocked = True
            self.send_message('You take the key and unlock the right door.')
          else:
            self.send_message('You try the right door, but it is locked.')

          self.right_checked = True
          return None

      case 'C':
        if self.central_left_unlocked and self.central_right_unlocked:
          self.send_message('You go through the center door.')
          self.world.player.set_parent(self.world.rooms['Central'])
          return None
        else:
          self.send_message('You try the center door, but it is locked.')
          return None

      case 'J':
        Jacket().set_parent(self.world.player)
        self.send_message('You take the jacket.')
        return None