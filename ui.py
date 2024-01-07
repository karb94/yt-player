from collections.abc import Sequence
from sqlalchemy import Row
from backend import Backend
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw
import signal



def buildCardsStack(videos: Sequence[Row]):
    list_box = Gtk.ListBox()
    for video in videos:
        # img = Gtk.Picture(file=img_path, vexpand=True, hexpand=True)
        img = Gtk.Picture.new_for_filename(video.thumbnail_path)
        img.props.halign = Gtk.Align.START
        img.props.can_shrink = False
        # img.set_hexpand(True)
        # box = Gtk.Grid(height_request=200, vscroll_policy=Gtk.ScrollablePolicy.NATURAL)
        box = Gtk.Grid()
        # box.set_property("height-request", 200)
        # box.props.height_request = 200
        box.attach(child=img, column=1, row=1, width=1, height=3) 
        title_label = Gtk.Label(
            label=f'<span weight="bold" size="x-large">{video.title}</span>',
            use_markup=True,
            halign=Gtk.Align.START,
            vexpand=True,
            margin_start=10,
        )
        box.attach(child=title_label, column=2, row=1, width=1, height=1) 
        channel_label = Gtk.Label(
            label=video.channel_title,
            halign=Gtk.Align.START,
            vexpand=True,
            margin_start=10,
        )
        box.attach(child=channel_label, column=2, row=2, width=1, height=1) 
        url_label = Gtk.Label(label=video.thumbnail_url, halign=Gtk.Align.START, vexpand=True, selectable=True, margin_start=10)
        box.attach(child=url_label, column=2, row=3, width=1, height=1) 
        list_box_row = Gtk.ListBoxRow()
        list_box_row.set_child(box)
        list_box.append(list_box_row)
    return list_box

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, backend: Backend, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = backend

        self.shortcut_hits = 0
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.label = Gtk.Label(label="")
        self.box.append(self.label)
        # self.box.append(self.scrolled_window)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.set_child(self.scrolled_window)
        videos = self.backend.query_videos()
        self.list_box = buildCardsStack(videos)
        # self.scrolled_window.set_child(self.list_box)
        self.box.append(self.list_box)
        self.scrolled_window.set_child(self.box)
        # self.button1 = Gtk.Button(label="Hello")
        # self.list_box.append(self.button1)

        evk = Gtk.EventControllerKey.new()
        evk.connect("key-pressed", self.key_press)
        self.add_controller(evk)

    def key_press(self, event, keyval, keycode, state):
        if keyval == Gdk.KEY_j: # and state & Gdk.ModifierType.CONTROL_MASK:
            print("Some key pressed", keyval)
            print(self.list_box.get_row_at_y(2))
            print(self.list_box.get_row_at_y(3))
            print(self.list_box.get_row_at_index(2))
            print(self.list_box.get_row_at_index(3))
            self.list_box.select_row(self.list_box.get_row_at_index(5))

    def on_key_press_event(self, widget, event):

        print("Key press on widget: ", widget)
        print("          Modifiers: ", event.state)
        print("      Key val, name: ", event.keyval, Gdk.keyval_name(event.keyval))

        # check the event modifiers (can also use SHIFTMASK, etc)
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        # see if we recognise a keypress
        if ctrl and event.keyval == Gdk.KEY_j:
            self.shortcut_hits += 1
            self.update_label_text()

    def update_label_text(self):
        # Update the label based on the state of the hit variable
        self.label.set_text(f"Shortcut pressed {self.shortcut_hits} times")


class MyApp(Adw.Application):
    def __init__(self, backend: Backend, **kwargs):
        self.backend = backend
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(backend=self.backend, application=app)
        self.win.present()

