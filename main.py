import os
import time

import gi
import threading
import requests

import gettext
_ = gettext.gettext

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject

_WINDOW_FILE = os.path.dirname(os.path.abspath(__file__)) + "/welcome.xml"
_PACKAGE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/package.xml"

quick_setup_packages = []


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id='io.risi.welcome', **kwargs)

        self.builder = Gtk.Builder()
        self.builder.add_from_file(_WINDOW_FILE)
        self.window = self.builder.get_object("main_window")
        self.quick_setup_stack = self.builder.get_object("quickSetupStack")

    def do_activate(self):
        self.window.set_application(self)
        self.window.present()

        self.builder.get_object("welcomeButton").connect("clicked", self.on_welcomeButton)

    def on_welcomeButton(self, button):
        button.set_label(_("Checking Internet Connection"))
        button.set_sensitive(False)
        internet_thread = threading.Thread(target=self.wait_for_internet)
        internet_thread.daemon = True
        internet_thread.start()

    def wait_for_internet(self):
        connected = False
        try:
            response = requests.get("https://nmcheck.gnome.org/check_network_status.txt")
            if "NetworkManager is online" in response.text:
                GLib.idle_add(
                    lambda: self.quick_setup_stack.set_visible_child(
                        self.builder.get_object("browserPage")
                    )
                )
        except requests.RequestException:
            GLib.idle_add(
                lambda: self.quick_setup_stack.set_visible_child(
                    self.builder.get_object("internetBox")
                )
            )
        while not connected:
            try:
                response = requests.get("https://nmcheck.gnome.org/check_network_status.txt")
                if "NetworkManager is online" in response.text:
                    connected = True
            except requests.RequestException:
                connected = False
        GLib.idle_add(lambda: self.quick_setup_stack.set_visible_child(
            self.builder.get_object("browserPage")
        ))


@Gtk.Template(filename=_PACKAGE_FILE)
class Package(Adw.ActionRow):
    __gtype_name__ = "Package"
    package_name = "package"
    icon_path = None
    _icon = Gtk.Image(pixel_size=32, margin_end=2)

    def __init__(self):
        super().__init__(self)
        self._icon = Gtk.Image(pixel_size=32, margin_end=2)
        self.add_prefix(self._icon)

        # switch = Gtk.Template.Child("switch")
        # switch.connect("notify::active", self.toggle_package)

    @GObject.Property(type=str)
    def package(self):
        return self.package_name

    @package.setter
    def package(self, name):
        self.package_name = name

    @GObject.Property(type=str)
    def icon_file(self):
        return self.icon_path

    @icon_file.setter
    def icon_file(self, icon):
        self.icon_path = os.path.dirname(os.path.abspath(__file__)) + f"/icons/{icon}"
        self._icon.set_from_file(self.icon_path)

    @Gtk.Template.Callback("toggle_package")
    def toggle_package(self, button):
        if button.get_active():
            quick_setup_packages.append(self.package_name)
        else:
            quick_setup_packages.remove(self.package_name)


if __name__ == "__main__":
    app = Application()
    app.run(None)