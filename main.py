import os

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
quick_setup_commands = []
quick_setup_extras = []


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
                        self.builder.get_object("repoPage")
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
            self.builder.get_object("repoPage")
        ))


@Gtk.Template(filename=_PACKAGE_FILE)
class Package(Adw.ActionRow):
    __gtype_name__ = "Package"
    package_name = None
    action_command = None
    action_extra = None
    icon_path = None
    internal_icon_name = None
    default = False
    icon = Gtk.Image(pixel_size=32, icon_size=Gtk.IconSize.LARGE, margin_end=2)

    switch = Gtk.Template.Child("switch")

    def __init__(self):
        super().__init__(self)
        self.add_prefix(self.icon)

    @Gtk.Template.Callback("on_update_defaults")
    def on_update_defaults(self):
        if self.default is True:
            self.switch.set_active(True)
        if self.icon_path is not None:
            self.icon.set_from_file(self.icon_path)
        if self.internal_icon_name is not None:
            self.icon.set_from_icon_name(self.internal_icon_name)

    @GObject.Property(type=str)
    def package(self):
        return self.package_name

    @package.setter
    def package(self, name):
        self.package_name = name

    @GObject.Property(type=str)
    def command(self):
        return self.action_name

    @command.setter
    def command(self, name):
        self.action_name = name

    @GObject.Property(type=str)
    def action(self):
        return self.action_extra

    @action.setter
    def action(self, name):
        self.action_extra = name

    @GObject.Property(type=str)
    def icon_file(self):
        return self.icon_path

    @icon_file.setter
    def icon_file(self, icon):
        self.icon_path = os.path.dirname(os.path.abspath(__file__)) + f"/icons/{icon}"
        self._icon.set_from_file(self.icon_path)

    @GObject.Property(type=str)
    def icon_name(self):
        return self._icon.get_icon_name()

    @icon_file.setter
    def icon_name(self, icon):
        self.internal_icon_name = icon

    @Gtk.Template.Callback("toggle_package")
    def toggle_package(self, button):
        if button.get_active():
            if self.package_name is not None:
                quick_setup_packages.append(self.package_name)
            if self.action_command is not None:
                quick_setup_commands.append(self.action_name)
            if self.action_extra is not None:
                quick_setup_extras.append(self.action_extra)
        else:
            if self.package_name is not None:
                quick_setup_packages.remove(self.package_command)
            if self.action_command is not None:
                quick_setup_commands.append(self.action_command)
            if self.action_extra is not None:
                quick_setup_extras.append(self.action_extra)

    @GObject.Property(type=bool, default=False)
    def switch_default(self):
        print(self.default)
        return self.default

    @switch_default.setter
    def switch_default(self, default):
        self.default = default

if __name__ == "__main__":
    app = Application()
    app.run(None)
