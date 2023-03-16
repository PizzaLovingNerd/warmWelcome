import os

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

_WINDOW_FILE = os.path.dirname(os.path.abspath(__file__)) + "/welcome.xml"
_PACKAGE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/package.xml"


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id='io.risi.welcome', **kwargs)

        self.builder = Gtk.Builder()
        handlers = {
            "on_welcomeButton_clicked": self.on_welcomeButton_clicked,
        }
        self.builder.connect_signals(handlers)
        self.builder.add_from_file(_WINDOW_FILE)
        self.window = self.builder.get_object("main_window")


    def do_activate(self):
        self.window.set_application(self)
        self.window.present()


    def on_welcomeButton_clicked(self, button):
        stack = self.builder.get_object("mainStack")
        stack.set_visible_child(self.builder.get_object("internetBox"))
        self.window.set_application(self)
        self.window.present()

if __name__ == "__main__":
    app = Application()
    app.run(None)