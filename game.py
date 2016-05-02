# TODO: roomscript
import glob
import urwid


class Key(object):
    """A key to any door usable once!

    """

    def __init__(self):
        self.name = "key"  # may be able to set in future


class Door(object):

    def __init__(self, link_id, needs_key=False):
        self.link_id = link_id
        self.needs_key = needs_key

    @property
    def name(self):

        return self.link_id


class Inventory(list):

    def iter_items_matching_name(self, name):
        """Don't use this, use the wrapper!"""

        for i, item in enumerate(self):

            if item.name.lower() == name.lower():
                yield i, item

    def iter_matched_items(self, func):

        def wrapped_func(name):

            for i, item in self.iter_items_matching_name(name):
                yield func(i, item)

        return wrapped_func

    def get_first_item_matching_name(self, name):

        for i, item in self.iter_items_matching_name(name):
            return item

        return None

    def has_item_of_name(self, name):

        for i, item in self.iter_items_matching_name(name):
            return True

        return False

    def remove_item_of_name(self, name):

        for i, item in self.iter_items_matching_name(name):
            del self[i]
            return None


class Player(object):

    def __init__(self, inventory=None):
        self.inventory = inventory or Inventory()


class Room(object):

    def __init__(self, link_id, title, exits, description, inventory=None):
        self.link_id = link_id
        self.title = title
        self.exits = exits
        self.description = description
        self.inventory = inventory or Inventory()

    def pickup_item(self, player, item_name):

        for inventory_index, item in enumerate(self.inventory):

            if item.name.lower() == item_name.lower():
                player.inventory.append(item)
                del self.inventory[inventory_index]
                return item

    @staticmethod
    def validate_and_clean(expected_row_name, unsafe_row):
        expected_row_name_with_syntax = expected_row_name.upper() + ": "
        assert unsafe_row.startswith(expected_row_name_with_syntax), (expected_row_name, unsafe_row)
        row_without_name = unsafe_row.replace(expected_row_name_with_syntax, " ", 1) 
        return row_without_name.strip()
    
    @classmethod
    def from_string(cls, room_string):
        """RoomScript"""

        room_file_contents = room_string.split('\n')
        link_id = cls.validate_and_clean("link_id", room_file_contents[0]).lower()
        title = cls.validate_and_clean("title", room_file_contents[1])

        # Exits are a little bit more complicated...
        exit_rules = cls.validate_and_clean("exits", room_file_contents[2]).split(",")
        exits = []

        for rule in exit_rules:

            if "[!LOCKED!]" in rule:
                door_is_locked = True
                link_name = rule.replace("[!LOCKED!]", "")
            else:
                door_is_locked = False
                link_name = rule

            door = Door(link_id=link_name, needs_key=door_is_locked)
            exits.append(door)

        # the room's items/inventory
        inventory_rules = cls.validate_and_clean("inventory", room_file_contents[3]).split(",")
        inventory = Inventory()

        for rule in inventory_rules:

            if rule:
                item_to_add = {"key": Key}[rule]
                inventory.append(item_to_add())

        # finally the description and make room
        description = '\n'.join(room_file_contents[4:]).strip()
        return cls(link_id, title, exits, description, inventory=inventory)


class Adventure(object):
    ROOM_NAME_PATTERN = "*.room.txt"

    def __init__(self, rooms):
        self.rooms = rooms
        self.player = Player()
        self.current_room = self.rooms["first_room"]

    @classmethod
    def from_directory(cls, directory):
        rooms = {}

        for room_file_name in glob.glob(directory + '/' + cls.ROOM_NAME_PATTERN):

            with open(room_file_name) as f:
                room_file_string = f.read()
                room = Room.from_string(room_file_string)
                rooms[room.link_id] = room

        return cls(rooms)

    def set_room_by_link_id(self, link_id):
        self.current_room = self.rooms[link_id]


class RoomUI(object):
    OVERLAY_WIDTH_IN_PERCENT = 60
    OVERLAY_HEIGHT_IN_PERCENT = 60

    def __init__(self, adventure):
        self.adventure = adventure
        self.main = None

    def menu(self):
        """Menu from current room.

        Needs to add thing for picking up items.

        """

        title = self.adventure.current_room.title.upper()
        description = self.adventure.current_room.description
        body = [urwid.Text(title),
                urwid.Divider(),
                urwid.Text(description),
                urwid.Divider()]

        for c in self.adventure.current_room.exits + self.adventure.current_room.inventory:
            button_name = c.name

            if hasattr(c, "needs_key") and c.needs_key:
                button_name += " [LOCKED]"

            button = urwid.Button(button_name)
            urwid.connect_signal(button, 'click', self.item_chosen, c.name)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))

        button = urwid.Button("QUIT")
        urwid.connect_signal(button, 'click', self.exit_program)
        body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        return urwid.ListBox(urwid.SimpleFocusListWalker(body))

    @staticmethod
    def exit_program(button):
        raise urwid.ExitMainLoop()

    def make_room(self):
        """GUI"""
        listbox_menu = self.menu()
        self.main.original_widget = listbox_menu

    def list_inventory(self):
        """asdf"""
        self.main.original_widget = new_thing

    def item_chosen(self, button, choice):
        """Can use this to create menu again.

        """

        # change the current room to choice
        # TODO: this should probably be a method of adventure,
        # such as getitem
        current_room = self.adventure.current_room

        for door in current_room.exits:

            if door.name.lower() == choice:

                if door.needs_key:
                    
                    if self.adventure.player.inventory.has_item_of_name('key'):
                        door.needs_key = False
                        self.adventure.player.inventory.remove_item_of_name('key')
                    else:
                        continue

                self.adventure.set_room_by_link_id(choice)
                self.make_room()
                return None

        current_room.pickup_item(self.adventure.player, choice)
        self.make_room()
        return None

    def run(self):
        listbox_menu = self.menu()
        self.main = urwid.Padding(listbox_menu, left=2, right=2)
        overlay_width = ('relative', self.OVERLAY_WIDTH_IN_PERCENT)
        overlay_height = ('relative', self.OVERLAY_HEIGHT_IN_PERCENT)
        top = urwid.Overlay(self.main, urwid.SolidFill(u'*'),
                            align='center', width=overlay_width,
                            valign='middle', height=overlay_height,
                            min_width=20, min_height=9)
        urwid.MainLoop(top, palette=[('reversed', 'standout', '')]).run()


# sorting out urwid gui mess
adventure = Adventure.from_directory("rooms")
RoomUI(adventure).run()
