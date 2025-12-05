from entities import *
class Notepad(Item):
  def __init__(self,name='Notepad'):
    super().__init__(name)
    self.notes = []

  def get_description(self) -> str:
    if self.parent == self.world.player:
      return 'You have a small notebook and pen.'
    else:
      return 'A small notepad and pen is sitting on a chair.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.parent == self.world.player:
      options.append((lambda : self.take_note(),'Take a note in the notepad.'))
      if len(self.notes) > 0:
        options.append((lambda : self.read_notes(),'Read your notes.'))

    else:
      options.append((lambda : self.take(),'Take the notepad and pen.'))

    return options

  def take(self):
    self.set_parent(self.world.player)
    self.send_message('You grab the notepad and pen.')

  def take_note(self):
    note = self.ask('Take a note. ')
    if len(note.strip()) > 0:
      self.notes.append(note)
      return None
    else:
      return None

  def read_notes(self):
    note_num = 0
    while note_num < len(self.notes):
      message = ''
      count = 0
      if note_num < len(self.notes):
        while count < 15:
          message += self.notes[note_num]+'\n'
          note_num += 1
          count += 1
          if note_num < len(self.notes):
            pass

      self.send_message(message)
      if note_num < len(self.notes):
        self.world.player.pause()

class Telephone(Item):
  def __init__(self,name='Telephone'):
    super().__init__(name)
    self.plugged_in = False
    self.tried_phone = False
    self.ready_for_number = False

  def get_description(self) -> str:
    return 'There is a blue phone on the counter.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.plugged_in:
      if self.tried_phone:
        options.append((lambda : self.plug_in(),'Plug in telephone'))
      else:
        options.append((lambda : self.use(),'Use telephone'))

    else:
      if self.ready_for_number:
        options.append((lambda : self.dial_extension(),'Dial an extension on the telephone'))
      else:
        options.append((lambda : self.use(),'Use telephone'))

    return options

  def plug_in(self):
    self.plugged_in = True
    self.send_message('You find the phone outlet and plug in the phone.')

  def use(self):
    if self.plugged_in:
      self.ready_for_number = True
      self.send_message('''You pick up the handset and listen...you hear pops and crackles.
You see a note next to the phone that says:
 --- To dial an extension, enter the 2 digits''')
      return None
    else:
      self.tried_phone = True
      self.send_message('You pick up the handset and listen...no dial tone.\nMaybe it\'s not plugged in.')
      return None

  def dial_extension(self):
    extension = self.ask_number('Enter 2 digit extension',2)
    if extension == self.world.player.age:
      self.send_message('''The pops and crackles stop.  It\'s quiet for few seconds.
Then a woman\'s voice says:
 --- Cat...Dog...Mouse''')
      return None
    else:
      self.send_message('You hear more pops and crackles...then a faint song in the background.\nIs that Happy Birthday?')
      return None

class Ticket(Item):
  def __init__(self,name='Ticket'):
    super().__init__(name)

  def get_description(self) -> str:
    return 'It\'s a red ticket with the number E5 on it.'

class TicketMachine(Item):
  def __init__(self,name='Ticket Machine'):
    super().__init__(name)
    self.broken = False

  def get_description(self) -> str:
    if self.broken:
      return 'The ticket machine parts lay broken on the floor.'
    else:
      pass
      return 'There is a dusty, classic ticket machine on a post next to the counter.  Maybe take a ticket so you know when it\'s your turn?'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.broken:
      options.append((lambda : self.use(),'Take a ticket.'))

    return options

  def use(self):
    self.broken = True
    self.send_message('''You take the next ticket from the machine.  Looks like you are E5.
The machine falls apart on the counter and kicks up a cloud of dust.
At least you have a ticket now.  Anyone else that shows up is out of luck.''')
    Ticket().set_parent(self.world.player)

class SignInSheet(Item):
  def __init__(self,name='Sign In Sheet'):
    super().__init__(name)
    self.sheet_read = False
    self.signed = False

  def get_description(self) -> str:
    return 'A sign in sheet is on the counter.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.read(),'Read the sign in sheet.'))
    if self.sheet_read and self.signed:
      options.append((lambda : self.use(),'Sign the sign in sheet.'))

    return options

  def read(self):
    self.sheet_read = True
    message = '''Looks like a sing in sheet for interviews.
These must be the previous people who tried to get a job here.
The list has:
 --- Hank Little
 --- Barbara James
 --- Chuck Huitt
 --- Emily Johnson'''
    if self.signed:
      message += '\n --- %s'%self.world.player.name

    self.send_message(message)

  def use(self):
    self.signed = True
    self.send_message('You scribble your name on the sing in sheet.')

class Lobby(Room):
  def __init__(self,name='Lobby'):
    super().__init__(name)
    self.is_opened = False
    Notepad().set_parent(self)
    Telephone().set_parent(self)
    TicketMachine().set_parent(self)
    SignInSheet().set_parent(self)

  def get_description(self) -> str:
    desc = '$div'
    desc += 'You are in a dusty room with a counter, and some chairs against the wall.\nThis must be the $room.'
    desc += 'You are in the $room.' if self.first_look else __CHAOS_PY_NULL_PTR_VALUE_ERR__
    for child in self.children:
      if child.get_visible() and child.is_a('Player'):
        child_desc = child.get_description()
        if len(child_desc) > 0:
          desc += '\n'+child_desc

    desc += '\nThere is a door past the counter with an "Employees Only" sign.'
    desc += '''
There is also a door to the left.

The door to leave $world is open.'''
    desc += '\nThere is also a door to the left and the door behind you where you entered the $world.' if self.is_opened else __CHAOS_PY_NULL_PTR_VALUE_ERR__
    return desc

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = super().get_options()
    options.append(('X','Try to leave.'))
    options.append(('F','Go through Employees Only door.'))
    options.append(('L','Go through left door.'))
    return options

  def handle_option_answer(self,value: str):
    match value:
      case 'X':
        if self.is_opened:
          self.send_message('You walk through the open door and everything goes white!')
          self.world.player.set_parent(self.world.rooms['Playroom'])
          return None
        else:
          self.send_message('The exit is locked.  You shake the door as hard as you can, but it doesn\'t open.\nYou don\'t see any lock, lever, or anything else to open it.')
          return None

      case 'F':
        self.send_message('You head forward through the door.')
        self.world.player.set_parent(self.world.rooms['Breakroom'])
        return None
      case 'L':
        self.send_message('You head through the left door.')
        self.world.player.set_parent(self.world.rooms['Gift Shop'])
        return None