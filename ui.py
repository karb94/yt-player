# import gi
# gi.require_version("Gtk", "3.0")
# from gi.repository import Gtk
#
#
# def buildCards(img_paths):
#     return list(map(Gtk.Image.new_from_file, img_paths))
#
#
# class MyWindow(Gtk.Window):
#     def __init__(self, imgs):
#         super().__init__(title="Hello World")
#
#         self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
#         self.add(self.box)
#
#         # self.button1 = Gtk.Button(label="Hello")
#         # self.button1.connect("clicked", self.on_button1_clicked)
#         # self.box.pack_start(self.button1, True, True, 0)
#
#         for img in imgs:
#             self.box.pack_end(img, True, True, 0)
#
#     # def on_button1_clicked(self, widget):
#     #     print("Hello")
#     #
#     # def on_button2_clicked(self, widget):
#     #     print("Goodbye")


import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here

class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()

app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
