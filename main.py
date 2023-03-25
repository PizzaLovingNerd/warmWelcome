import os

import gi
import threading
import requests

import gettext

import urllib3

_ = gettext.gettext

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject

_WINDOW_FILE = os.path.dirname(os.path.abspath(__file__)) + "/welcome.xml"
_PACKAGE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/package.xml"
_NAVIGATION_ROW_FILE = os.path.dirname(os.path.abspath(__file__)) + "/navigation_row.xml"
_CATEGORY_CHOOSER_FILE = os.path.dirname(os.path.abspath(__file__)) + "/category_chooser.xml"

packages = []

quick_setup_packages = []
quick_setup_commands = []
quick_setup_extras = []


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id='io.risi.welcome', **kwargs)
        self.set_resource_base_path(os.path.dirname(os.path.abspath(__file__)) + "/style.css")

        self.builder = Gtk.Builder()
        self.builder.add_from_file(_WINDOW_FILE)
        self.window = self.builder.get_object("main_window")
        self.quick_setup_stack = self.builder.get_object("quickSetupStack")

    def get_widget_id(self, widget):
        return self.builder.get_object(widget)

    def reveal_app_list(self, page):
        self.builder.get_object("additionalProgramsStack").set_visible_child(
            self.builder.get_object(page)
        )

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

    def wait_for_internet_idle(self, page_id):
        self.quick_setup_stack.set_visible_child(self.builder.get_object(page_id))
        button = self.builder.get_object("welcomeButton")
        button.set_label(_("Get Started"))
        button.set_sensitive(True)

    def wait_for_internet(self):
        connected = False
        try:
            response = requests.get("https://nmcheck.gnome.org/check_network_status.txt")
            if "NetworkManager is online" in response.text:
                GLib.idle_add(self.wait_for_internet_idle, "repoPage")
        except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError):
            GLib.idle_add(
                self.wait_for_internet_idle, "internetBox"
            )
        while not connected:
            try:
                response = requests.get("https://nmcheck.gnome.org/check_network_status.txt")
                if "NetworkManager is online" in response.text:
                    connected = True
            except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError):
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
    rpmfusion = False
    icon = Gtk.Template.Child("icon_image")
    switch = Gtk.Template.Child("switch")

    def __init__(self):
        super().__init__(self)
        packages.append(self)

    @Gtk.Template.Callback("on_update_defaults")
    def on_update_defaults(self, *args, **kwargs):
        if self.default is True:
            self.switch.set_active(True)
        if self.icon_path is not None:
            self.icon.set_from_file(self.icon_path)
        if self.internal_icon_name is not None:
            self.icon.set_from_icon_name(self.internal_icon_name)

    @Gtk.Template.Callback("toggle_package")
    def toggle_package(self, button):
        if button.get_active():
            if self.package_name is not None:
                quick_setup_packages.append(self.package_name)
            if self.action_command is not None:
                quick_setup_commands.append(self.action_name)
            if self.action_extra is not None:
                quick_setup_extras.append(self.action_extra)
                for package in packages:
                    package.check_rpmfusion()
        else:
            if self.package_name is not None:
                quick_setup_packages.remove(self.package_name)
            if self.action_command is not None:
                quick_setup_commands.remove(self.action_name)
            if self.action_extra is not None:
                quick_setup_extras.remove(self.action_extra)
                for package in packages:
                    package.check_rpmfusion()

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
    def iconfile(self):
        return self.icon_path

    @iconfile.setter
    def iconfile(self, icon):
        self.icon_path = os.path.dirname(os.path.abspath(__file__)) + f"/icons/{icon}"

    @GObject.Property(type=str)
    def iconname(self):
        return self.internal_icon_name

    @iconname.setter
    def iconname(self, icon):
        self.internal_icon_name = icon

    @GObject.Property(type=bool, default=False)
    def switch_default(self):
        return self.default

    @switch_default.setter
    def switch_default(self, default):
        self.default = default

    @GObject.Property(type=bool, default=False)
    def rpmfusion_required(self, required):
        return self.rpmfusion

    @rpmfusion_required.setter
    def rpmfusion_required(self, required):
        self.rpmfusion = required

    # @Gtk.Template.Callback("check_rpmfusion")
    def check_rpmfusion(self):
        if self.rpmfusion == True:
            if "rpmfusion" not in quick_setup_extras:
                self.set_sensitive(False)
            else:
                self.set_sensitive(True)


@Gtk.Template(filename=_NAVIGATION_ROW_FILE)
class NavigationRow(Adw.ActionRow):
    __gtype_name__ = "NavigationRow"
    next_page_id = None
    previous_page_id = None
    stack_id = None
    back_btn = Gtk.Template.Child("back_btn")
    next_btn = Gtk.Template.Child("next_btn")

    @GObject.Property(type=str)
    def next_page(self):
        return self.next_page_id

    @next_page.setter
    def next_page(self, page):
        self.next_page_id = page

    @GObject.Property(type=str)
    def previous_page(self):
        return self.previous_page_id

    @previous_page.setter
    def previous_page(self, page):
        self.previous_page_id = page

    @GObject.Property(type=str)
    def stack(self):
        return self.stack_id

    @stack.setter
    def stack(self, stack):
        self.stack_id = stack

    @Gtk.Template.Callback("on_next_page")
    def on_next_page(self, button):
        application = button.get_root().get_application()
        application.builder.get_object(self.stack_id).set_visible_child(
            application.builder.get_object(self.next_page_id)
        )

    @Gtk.Template.Callback("on_previous_page")
    def on_previous_page(self, button):
        application = button.get_root().get_application()
        application.builder.get_object(self.stack_id).set_visible_child(
            application.builder.get_object(self.previous_page_id)
        )

    @Gtk.Template.Callback("show_buttons")
    def show_buttons(self, *args, **kwargs):
        self.back_btn.set_visible(self.previous_page_id is not None)
        self.next_btn.set_visible(self.next_page_id is not None)


@Gtk.Template(filename=_CATEGORY_CHOOSER_FILE)
class CategoryChooser(Adw.ActionRow):
    __gtype_name__ = "CategoryChooser"
    _page = None
    icon_path = None
    internal_icon_name = None
    icon = Gtk.Template.Child("icon_image")

    def __init__(self):
        super().__init__()

    @Gtk.Template.Callback("btn_clicked")
    def btn_clicked(self, button):
        application = button.get_root().get_application()
        application.reveal_app_list(self._page)

    @GObject.Property(type=str)
    def page(self):
        return self._page

    @page.setter
    def page(self, name):
        self._page = name

    @GObject.Property(type=str)
    def iconfile(self):
        return self.icon_path

    @iconfile.setter
    def iconfile(self, icon):
        self.icon_path = os.path.dirname(os.path.abspath(__file__)) + f"/icons/{icon}"

    @GObject.Property(type=str)
    def iconname(self):
        return self.internal_icon_name

    @iconname.setter
    def iconname(self, icon):
        self.internal_icon_name = icon

    @Gtk.Template.Callback("on_update_defaults")
    def on_update_defaults(self, *args, **kwargs):
        if self.icon_path is not None:
            self.icon.set_from_file(self.icon_path)
        if self.internal_icon_name is not None:
            self.icon.set_from_icon_name(self.internal_icon_name)

if __name__ == "__main__":
    app = Application()
    app.run(None)
