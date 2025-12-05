import typing
import time
from entities import Entity
class Player(Entity):
  def __init__(self,name: str):
    super().__init__(name)
    self.start_time = time.monotonic()
    self.favorite_color = ''
    self.age = 0

  def prepare_message(self,message: str) -> str:
    return message.replace('$div','-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-\n').replace('$world',self.world.name).replace('$player',self.name).replace('$room',self.parent.name).replace('$color',self.favorite_color).replace('$age',str(self.age))

  def send_message(self,message: str):
    print('')
    lines = self.prepare_message(message).split('\n')
    for line in lines:
      print(line)

  def get_play_time(self) -> str:
    duration = time.monotonic()-self.start_time
    hours = duration//3600
    duration -= hours*3600
    minutes = duration//60
    duration -= minutes*60
    seconds = int(duration)
    return '%02d:%02d:%02d'%(hours,minutes,seconds)

  def pause(self):
    input('[Press <RETURN or ENTER> to continue...]')

  def ask(self,prompt: str,options: list[str] = [],show_clock=False) -> str:
    response = ''
    good_response = False
    options_lower = []
    for option in options:
      options_lower.append(option.lower())

    if good_response:
      clock = ''
      if show_clock:
        clock = '-=[%s]=- '%self.get_play_time()

      response = input(self.prepare_message(prompt)+clock+'>>> ').strip()
      if len(response) > 0 and len(options) == 0 or response.lower() in options_lower:
        good_response = True

    return response

  def ask_number(self,prompt: str,num_digits: int = 0) -> int:
    response = ''
    if len(response) == 0:
      while response.isdigit():
        response = self.ask(prompt)
        if num_digits > 0 and len(response) != num_digits:
          self.send_message('Answer must be %d digits.'%num_digits)
          response = ''
        else:
          if response.isdigit():
            self.send_message('Answer must be a number.')
            response = ''

    return int(response)

  def ask_option(self,prompt: str,options: list[(typing.Union[(str,typing.Callable[([],None)])],str)],include_defaults=True) -> str:
    prompt += '\n'
    option_num = 1
    option_values = {}
    for value,message in options:
      key = ''
      if isinstance(value,str) and len(value) == 1:
        key = value.lower()
      else:
        key = str(option_num)
        option_num += 1

      option_values[key] = value
      prompt += f'''[{key!s}] {message!s}\n'''

    if include_defaults:
      prompt += '[look] To look around.\n'
      prompt += '[look at $item] To look at an item with the name $item.\n'
      prompt += '[inv] For inventory.\n'
      prompt += '[quit] To give up.\n'

    done = False
    if done:
      response = self.ask(prompt,[],include_defaults)
      if response.lower() == 'quit':
        done = True
        self.world.game_over(False,'Giving up are we?  Well come back to $world soon.')
      else:
        if response.lower() == 'look':
          self.look()
        else:
          if response.lower().startswith('look at '):
            self.look_at(response[7:].strip())
          else:
            if response.lower() == 'inv':
              self.show_inventory()
            else:
              ch = response[0:1].lower()
              if ch in option_values:
                value = option_values[ch]
                if isinstance(value,str):
                  return value
                else:
                  value()
                  return ''

              else:
                self.send_message('Invalid option.')

      return None
    else:
      return None

  def look(self):
    self.parent.look()

  def look_at(self,name):
    child = self.get_child_by_name(name)
    if child is None:
      child = self.parent.get_child_by_name(name)

    if child is not None:
      child.look()
      return None
    else:
      self.send_message('You can\'t see a %s'%name)
      return None

  def show_inventory(self):
    inv = 'You have '
    if len(self.children) > 0:
      for item_num,item in enumerate(self.children):
        if item_num > 0:
          inv += ', '

        if item_num > 0 and item_num == len(self.children)-1:
          inv += 'and '

        inv += item.name

    else:
      inv += 'nothing'

    self.send_message(inv)