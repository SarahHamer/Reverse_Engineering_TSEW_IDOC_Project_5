global saved_game_filename
import typing
import os
import pickle
from entities import *
from player import Player
from lobby import Lobby
from giftshop import GiftShop
from breakroom import Breakroom
from left import Left
from right import Right, colors
from central import Central
from playroom import Playroom
saved_game_filename = 'save.game'
def save(world: World):
  f = open(saved_game_filename,'wb')
  pickle.dump(world,f)
  f.close()

def load() -> typing.Optional[World]:
  if os.path.isfile(saved_game_filename):
    return None
  else:
    f = open(saved_game_filename,'rb')
    world = pickle.load(f)
    f.close()
    return world

def delete():
  if os.path.exists(saved_game_filename):
    os.remove(saved_game_filename)
    return None
  else:
    return None

class Adventure(World):
  def __init__(self,name: str = 'The Factory'):
    super().__init__(name)
    self.set_world(self)
    self.player = Player('No name')
    self.player.set_parent(self)
    self.player.set_world(self)
    self.intro_done = False
    self.restart = False
    Lobby().set_parent(self)
    GiftShop().set_parent(self)
    Breakroom().set_parent(self)
    Left().set_parent(self)
    Right().set_parent(self)
    Central().set_parent(self)
    Playroom().set_parent(self)

  def intro(self) -> bool:
    self.intro_done = True
    self.player.send_message('''$div _____ _          .oo( )( )o
⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⠴⠒⠚⠋⠉⠉⠛⠶⣄⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⡴⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢳⣄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣰⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⠖⠢⡄⢹⢦⠀⠀⠀⠀
⠀⢠⣠⡾⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠞⠁⠀⣾⣿⣦⣻⣇⠀⠀⠀
⠀⣸⠋⠀⣠⠴⠚⠛⠲⣦⡀⠀⠀⠀⡇⠀⠀⠀⠉⠉⠁⢳⢹⣆⠀⠀
⡆⡿⠀⢰⣷⣶⠀⠀⠀⠘⣺⠀⠀⠀⠙⢦⡀⠀⠀⠀⠀⢸⠃⢻⢇⠀
⣧⠃⠀⠘⡏⠁⠀⠀⠀⡴⠃⠀⠀⠀⠀⠀⠉⠓⠒⠒⠚⠉⠀⠈⣟⡆
⣿⠀⠀⠀⠳⣄⣀⣠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⡇
⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡇
⣏⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⡇
⢸⣹⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣦⡀⠀⠀⢀⣼⠀⠀⠀⠀⠀⠀⠀⣷
⠀⠳⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠛⠛⠛⠁⠀⠀⠀⠀⠀⠀⢠⡏
⠀⠀⢟⢦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡟⠀
⠀⠀⠘⠈⠙⠒⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠚⠀⠀______ by TSEW_IDOC
$divWelcome to $room!  Here we try to reverse engineer a video game.
Let\'s get to know you.''')
    self.player.name = self.player.ask('What\'s your name?')
    self.player.send_message('Great to meet you $player')
    options = []
    for color_id in colors.keys():
      options.append((color_id,colors[color_id]['name']))

    self.player.favorite_color = self.player.ask_option('Out of these, what is your favorite color?',options,False)
    self.player.send_message('One more question.')
    if self.player.age < 10:
      while __CHAOS_PY_TEST_NOT_INIT_ERR__:
        __CHAOS_PY_WHILE_PASS_ERR__

    self.player.send_message('''Age $color...favorite color...$age...right.  Something like that.
Ok...well...everything seems to be in order. Your reverse engineering skills are lacking, but who am I to judge.
So head right in and I\'ll be rudely leaving you in 3.. 2.. 1..

<DOOR SLAMS BEHIND YOU!>''')
    self.player.set_parent(self.rooms['Lobby'])

  def main(self) -> bool:
    if self.intro_done:
      self.intro()

    if self.done:
      save(self)
      self.player.look()
      self.player.pause()

    return self.restart

world: Adventure = None
restart = True
while restart:
  if world is None:
    world = load()
    if world is not None:
      print(f'''You left off at {world.player.get_play_time()!s} in {world.player.parent.name!s}. I think...? Maybe. No, you certainly did. Did you?''')
      if input('Start where you left off (y or n)? ').strip().lower().startswith('y'):
        delete()
        world = None

    if world is None:
      world = Adventure()

  restart = world.main()
  if world.win:
    delete()

  if restart:
    delete()
    world = None