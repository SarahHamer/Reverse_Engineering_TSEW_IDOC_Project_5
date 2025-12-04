from entities import *
class HistoryBook(Item):
  def __init__(self,name='History Book'):
    super().__init__(name)

  def get_description(self) -> str:
    pass
    return 'A $color paper bound book labeled "$world and Interesting History" $age anniversary edition.\nIt looks like it\'s water damaged, but there are some pages that are still readable.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = [(lambda : self.read(),'Read History Book')]
    return options

  def read(self):
    chapters = [('1','What is $world'),('2','The Founders'),('5','How We Do Things Here'),('8','$world Map')]
    chapter = self.ask_option('What chapter do you want to read?',chapters,False)
    message = ''
    print('Chapter: __%s__'%chapter)
    match chapter:
      case '1':
        message = '''$world is where we solve problems big or small.  We have a "unique" way of doing
things here that has proven to deliver results.
What do we do here $player?  Well, we create the fut... <INK IS SMUDGED>
...an opportunity we don\'t take lightly.'''
      case '2':
        message = '''$world was founded $age years ago by doctors Mo... <NAME IS SMUDGED> and D.. <NAME IS SMUDGED>.
This was their gift to the world.  An opportunity to make things better.
From it\'s inception they have nurtured it and watched it grow in the the powerhouse
it is today.

Sadly 3 years ago...<THE REST IS UNREADABLE>'''
      case '5':
        message = '''Here at $world we take on a lot of different problems.  The variety is pretty impressive.
To accomplish this, we start by breaking things down in to two categories.
If the problem is more technical or analytical, we send that off to the left wing of $world.
On the other hand, if the problem is creative or design problem, that does to...<INK IS SMUDGED>
...or more complicated issues go to the Central Department.'''
      case '8':
        message = '''         ┌────────────────┐
         │                │
         │     Central    │
         │                │
┌──────┐ └─────┬─┬────────┘
│      │       │ │
│ Left │   ┌───┴─┴─────┐  ┌───────┐
│ Wing ├───┤           │  │       │
│      ├───┤ Breakroom ├──┤       │
│      │   │           ├──┤ Right │
└──────┘   └────┬─┬────┘  │ Wing  │
                │ │       │       │
 ┌──────┐  ┌────┴─┴──┐    │       │
 │      │  │         │    │       │
 │ Gift ├──┤  Lobby  │    └───────┘
 │ Shop ├──┤         │
 │      │  └────┬─┬──┘
 └──────┘       └─┘'''

    self.world.player.send_message(message)

class Dollar(Item):
  def __init__(self,name='Dollar'):
    super().__init__(name)

  def get_description(self) -> str:
    return 'A dollar.'

class CashRegister(Item):
  def __init__(self,name='Cash Register'):
    super().__init__(name)
    self.is_open = False
    self.money_taken = False

  def get_description(self) -> str:
    if self.is_open:
      return 'There is a cash register in the corner.'
    else:
      if self.money_taken:
        return 'There is a cash register in the corner with a dollar in it.'
      else:
        return 'There is an empty cash register in the corner.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    if self.is_open:
      options.append((lambda : self.open(),'Open the cash register.'))
    else:
      if self.money_taken:
        options.append((lambda : self.take_money(),'Take dollar from cash register.'))

    return options

  def open(self):
    self.is_open = True
    self.world.player.send_message('You press a button and open the cash register.  There is a dollar in it.')

  def take_money(self):
    self.money_taken = True
    self.world.player.send_message('You take the dollar.')
    Dollar().set_parent(self.world.player)

class GiftShop(Room):
  def __init__(self,name='Gift Shop'):
    super().__init__(name)
    self.book_taken = False
    CashRegister().set_parent(self)

  def get_description(self) -> str:
    desc = '$div'
    desc += '''You\'re in a room with a bunch of shelves that are mostly empty.
The shelves do have a couple broken bobble-head dolls, some plush
hammers and wrenches with stuffing coming out, and a stack of books
labeled "$world and Interesting History".
This must be a $room.'''
    desc += 'You are in the $room.  You see some broken merch and a stack of books labeled "$world and Interesting History".' if self.first_look else __CHAOS_PY_NULL_PTR_VALUE_ERR__
    for child in self.children:
      if child.get_visible() and child.is_a('Player'):
        child_desc = child.get_description()
        if len(child_desc) > 0:
          desc += '\n'+child_desc

    desc += '\nThere is a door to the right back to the Lobby.'
    return desc

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = super().get_options()
    options.append(('R','Go through right door to the Lobby.'))
    if self.book_taken:
      options.append(('H','Grab a History Book.'))

    return options

  def handle_option_answer(self,value: str):
    match value:
      case 'R':
        self.send_message('You head through the right door.')
        self.world.player.set_parent(self.world.rooms['Lobby'])
        return None
      case 'H':
        self.book_taken = True
        self.send_message('You take one of the history books.')
        HistoryBook().set_parent(self.world.player)
        return None