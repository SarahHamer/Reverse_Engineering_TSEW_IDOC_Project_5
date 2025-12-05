import typing

class Entity:
    def __init__(self, name: str):
        self.name = name
        self.world = None
        self.parent = None
        self.children = []
        self.first_look = True

    def is_a(self, entity_type) -> bool:
        # fixing if : error that is most likely due to decompiling
        try:
            if isinstance(entity_type, str):
                # Look up class name in global scope
                entity_type = globals().get(entity_type, None)
                if entity_type is None:
                    return False

            return isinstance(self, entity_type)
        except:
            return False

    def set_world(self, world):
        self.world = world
        for child in self.children:
            child.set_world(self.world)
        return self

    def set_parent(self, parent):
        if self.parent is not None:
            self.parent.remove_child(self)

        if parent is not None:
            parent.add_child(self)
            self.parent = parent

        if parent.world is not None:
            self.set_world(parent.world)
        else:
            if parent.is_a('World'):
                self.set_world(parent)

        parent = parent.parent
        return self

    def add_child(self, child):
        self.children.append(child)
        child.set_world(self.world)
        return self

    def remove_child(self, child):
        self.children.remove(child)
        return self

    def get_child_by_type(self, entity_type):
        for child in self.children:
            if child.is_a(entity_type):
                child
                return
            else:
                continue

    def get_child_by_name(self, name: str):
        for child in self.children:
            if child.name.lower() == name.lower():
                child
                return
            else:
                continue

    def get_description(self) -> str:
        return ''

    def get_visible(self) -> bool:
        return True

    def look(self):
        if self.world is not None and self.world.player is not None:
            self.world.player.send_message(self.get_description())
            self.first_look = False
            return None
        else:
            return None
            return None

    def send_message(self, message: str):
        if self.world is not None and self.world.player is not None:
            self.world.player.send_message(message)
            return None
        else:
            return None
            return None

    def ask(self, prompt: str, options: list[str] = []) -> str:
        if self.world is not None and self.world.player is not None:
            return self.world.player.ask(prompt, options)
        else:
            return ''

    def ask_number(self, prompt: str, num_digits: int = 0) -> int:
        if self.world is not None and self.world.player is not None:
            return self.world.player.ask_number(prompt, num_digits)
        else:
            return 0

    def get_options(self) -> list[(typing.Union[(str, typing.Callable[([], None)])], str)]:
        options = []
        for child in self.children:
            if child.get_visible():
                for child_option in child.get_options():
                    options.append(child_option)
        return options

    def ask_option(self, prompt: str,
                   options: list[(typing.Union[(str, typing.Callable[([], None)])], str)],
                   include_defaults=True) -> str:
        if self.world is not None and self.world.player is not None:
            return self.world.player.ask_option(prompt, options, include_defaults)
        else:
            return ''


class Item(Entity):
    def __init__(self, name: str):
        super().__init__(name)


class Room(Entity):
    def __init__(self, name: str):
        super().__init__(name)

    def get_options_prompt(self):
        return 'What would you like to do?'

    def handle_option_answer(self, value: str):
        return None

    def look(self):
        super().look()
        if self.world is not None and self.world.player is not None:
            self.handle_option_answer(
                self.world.player.ask_option(self.get_options_prompt(), self.get_options())
            )
            return None
        else:
            return None
            return None


class World(Entity):
    def __init__(self, name: str):
        super().__init__(name)
        self.rooms = {}
        self.player = None
        self.done = False
        self.win = False

    def add_child(self, child):
        super().add_child(child)
        if child.is_a(Room):
            self.rooms[child.name] = child
            return None
        else:
            return None

    def game_over(self, win: bool, message: str):
        self.player.send_message(message)
        self.player.send_message('You took %s' % self.player.get_play_time())
        self.win = win
        self.done = True
