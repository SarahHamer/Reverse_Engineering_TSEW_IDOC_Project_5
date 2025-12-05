from entities import *
class Drawings(Item):
  def __init__(self,name='Drawings'):
    super().__init__(name)
    self.checked = False

  def get_description(self) -> str:
    return 'There are crayon drawings on the walls.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.check(),'Check out the crayon drawings on the walls.'))
    return options

  def check(self):
    self.checked = True
    self.send_message('''You check out all of the crayon drawings on the walls.
You see 4 drawings of people in suits and lab coats.  They have names on them:
 --- Hank Little
 --- Barbara James
 --- Chuck Huitt
 --- Emily Johnson

You remember!  Those are your brothers and sisters Hank, Barbara, Chuck, and Emily!

All of you would play together and make up names and pretend you all worked together.
They were never as imaginative as you, so would always use their real first names.

This makes you smile.

You also see a crayon drawing of someone in a flannel jacket.  It says:
 --- Employee of the month - $player
 --- aka - Sam Heart

That\'s you!  You remember!
Your name is Sam Heart!

You feel the emotion and tears welling up.

What is happening?''')

class FactoryModel(Item):
  def __init__(self,name='Factory Model'):
    super().__init__(name)
    self.checked = False

  def get_description(self) -> str:
    return 'A toy model of a building is in the middle of the room.'

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = []
    options.append((lambda : self.check(),'Check out the toy model.'))
    return options

  def check(self):
    self.checked = True
    self.send_message('''You check out the toy model in the middle of the room.
It\'s made of small boxes, some paper tubes, and what look like pieces of
various other toys.  It looks like it has 6 rooms connected with hallways.
The paper tubes look like smoke stacks.  There are pieces of wire taped down
and running between the rooms to make it look high-tech.

One of the rooms is covered with colorful stickers and drawings of music notes.
Another room has math equations and pictures of the brain draw on it.
There is a sign taped to the building that says:
 --- $world

This was your favorite game to play with your brothers and sisters!
You would pretend to be scientists, artists, and leaders trying to solve
the worlds problems.

You felt like you could accomplish anything!

But why are you here now?''')

class Playroom(Room):
  def __init__(self,name='Playroom'):
    super().__init__(name)
    Drawings().set_parent(self)
    FactoryModel().set_parent(self)

  def get_description(self) -> str:
    desc = '$div'
    desc += '''Nostalgia overwhelms you!  You look around and see your childhood.
You are in a simple room surrounded by crayon drawings.  Your eyes
widen as you realize they are yours!  This is your playroom as a child.'''
    desc += 'You are in your playroom.' if self.first_look else __CHAOS_PY_NULL_PTR_VALUE_ERR__
    for child in self.children:
      if child.get_visible() and child.is_a('Player'):
        child_desc = child.get_description()
        if len(child_desc) > 0:
          desc += '\n'+child_desc

    desc += '''
You feel very safe here, but what is going on?  Are you dreaming?
'''
    return desc

  def get_options(self) -> list[(typing.Union[(str,typing.Callable[([],None)])],str)]:
    options = super().get_options()
    if self.get_child_by_type(Drawings).checked and self.get_child_by_type(FactoryModel).checked:
      options.append(('P','Pinch yourself to wake up.'))
      options.append(('S','Stay here and keep play where it\'s safe.'))

    return options

  def handle_option_answer(self,value: str):
    match value:
      case 'P':
        self.send_message('''You pinch yourself.
You are no longer in the playroom.
You hear beeping as you open your eyes.  You can\'t quite focus yet,
but you can tell you are laying down.
You can start to make out white walls around you.  You are in a bed.

You can hear excited people talking and footsteps coming close:

 --- Sam is waking up!

You feel someone hold your hand.  You look to your left as your vision becomes more clear.

 --- Mom! ... Dad!

''')
        self.world.game_over(True,'Congratulations!')
        return None
      case 'S':
        self.world.restart = True
        self.world.game_over(True,'You decide to stay here and continue to play.')
        return None