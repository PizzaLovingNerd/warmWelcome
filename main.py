import os
import shutil
import subprocess
import tempfile

import gi
import threading
import requests
import json

import gettext

import urllib3
_ = gettext.gettext

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Vte", "3.91")
from gi.repository import Gtk, Adw, Vte, GLib, GObject, GdkPixbuf

_WINDOW_FILE = os.path.dirname(os.path.abspath(__file__)) + "/welcome.xml"
_PACKAGE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/package.xml"
_NAVIGATION_ROW_FILE = os.path.dirname(os.path.abspath(__file__)) + "/navigation_row.xml"
_SIDEBAR_BUTTON_FILE = os.path.dirname(os.path.abspath(__file__)) + "/sidebar_button.xml"
_CATEGORY_CHOOSER_FILE = os.path.dirname(os.path.abspath(__file__)) + "/category_chooser.xml"
_LAUNCHER_FILE = os.path.dirname(os.path.abspath(__file__)) + "/launcher.xml"
_TOUR_FILE = os.path.dirname(os.path.abspath(__file__)) + "/tour.xml"
_TOUR_PAGE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/tour_page.xml"
_PW_PROMPTER = os.path.dirname(os.path.abspath(__file__)) + "/prompter.sh"

packages = []

quick_setup_packages = []
quick_setup_commands = []
quick_setup_extras = []
welcome_sidebar_buttons = []

# Checking GPU Vendor
lshw_data = None
print("IGNORE THE WARNING BELOW, THIS DOES NOT AFFECT THE PROGRAM")
lshw = subprocess.Popen("lshw -C display", shell=True, stdout=subprocess.PIPE)
lshw_data = lshw.stdout.read().decode("utf-8")
vendor_line = lshw_data.split("vendor: ")[1].split("\n")[0]
if "nvidia" in vendor_line.lower():
    quick_setup_extras.append("nvidia")
elif "amd" in vendor_line.lower():
    quick_setup_extras.append("amd")
elif "intel" in vendor_line.lower():
    quick_setup_extras.append("intel")

actions = {
    "rpmfusion": [
        "echo Installing RPMFusion Repositories",
        "dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm",
        "echo Updating AppStream",
        "dnf groupupdate core",
        "echo Installing Multimedia Packages",
        "dnf groupupdate multimedia --setop=\"install_weak_deps=False\" --exclude=PackageKit-gstreamer-plugin",
        "echo Sound & Video Packages",
        "dnf groupupdate sound-and-video"
    ],
    "flatpak": [
        "echo Installing Flatpak",
        "dnf install -y flatpak",
        "echo Adding Flathub",
        "flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo",
        "echo Adding Theme Overrides",
        "flatpak override --filesystem=~/.themes",
        "flatpak override --filesystem=/usr/share/themes",
        "flatpak override --filesystem=xdg-config/gtk-4.0",
        "flatpak override --filesystem=xdg-config/gtk-3.0"
    ],
    "nvidia": [],
    "amd": [],
    "intel": []
}
package_groups = {}


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id='io.risi.welcome', **kwargs)
        self.set_resource_base_path(os.path.dirname(os.path.abspath(__file__)) + "/style.css")

        self.builder = Gtk.Builder()
        self.builder.add_from_file(_WINDOW_FILE)
        self.window = self.builder.get_object("main_window")
        self.quick_setup_stack = self.builder.get_object("quickSetupStack")

        self.vte = Vte.Terminal(vexpand=True, hexpand=True)
        self.vte.set_input_enabled(False)
        self.builder.get_object("vteBox").append(self.vte)

        self.welcome_leaflet = self.builder.get_object("welcomeLeaflet")
        
    def do_activate(self):
        self.window.set_application(self)
        self.window.maximize()
        self.window.present()

        self.builder.get_object("additionalProgramsBack").connect(
            "clicked", self.on_additionalProgramsBackClicked
        )
        self.builder.get_object("welcomeButton").connect("clicked", self.on_welcomeButton)
        self.builder.get_object("progressButton").connect("clicked", self.view_progress)
        self.builder.get_object("installationBack").connect("clicked", self.on_installationBackClicked)
        self.vte.connect("child_exited", self.terminal_exited)
        self.builder.get_object("mainStack").set_visible_child(    # DEBUGGING
            self.builder.get_object("welcomeLeaflet")
        )

        self.builder.get_object("welcomeStack").connect("notify::visible-child", self.on_welcome_stack_switched)
        self.welcome_leaflet.connect("notify::folded", self.on_welcome_leaflet_unfoldable)
        self.welcome_leaflet.navigate(Adw.NavigationDirection.FORWARD)

    def terminal_exited(self, terminal, status):
        self.builder.get_object("installSpinner").stop()
        if not self.builder.get_object("main_window").get_visible():
            self.builder.get_object("main_window").set_visible(True)
        if status != 0:
            print(status)
            if status == 126:  # This currently doesn't work due to a bug in VTE upstream
                dialog = Adw.MessageDialog(
                    heading=_("Error: Authentication Failed"),
                    body=_("You have not entered your password correctly 3 times. Please try again."),
                    transient_for=self.window
                )
                dialog.add_response("again", _("Try Again"))
                dialog.add_response("close", _("Close Welcome"))
                dialog.connect("response", self.on_dialogs)
                dialog.choose()
            else:
                dialog = Adw.MessageDialog(
                    heading=_("Error: Exit code not 1"),
                    body=_("An unknown error has occurred"),
                    transient_for=self.window
                )
                dialog.add_response("logs", _("View Logs"))
                dialog.add_response("again", _("Try Again"))
                dialog.add_response("close", _("Close Welcome"))
                dialog.connect("response", self.on_dialogs)
                dialog.choose()
        else:
            dialog = Adw.MessageDialog(
                heading=_("Quick Setup Complete"),
                body=_("Your system has been successfully configured. We recommend rebooting your system now."),
                transient_for=self.window
            )
            dialog.add_response("reboot", "Reboot now")
            dialog.add_response("close", "Reboot later")
            dialog.connect("response", self.on_dialogs)
            dialog.choose()

    def on_dialogs(self, dialog, response):
        if response == "close":
            self.quit()
        elif response == "logs":
            self.builder.get_object("runningStack").set_visible_child(
                self.builder.get_object("vteBox")
            )
            self.builder.get_object("installationBack").set_sensitive(False)
            self.builder.get_object("main_window").set_hide_on_close(False)
        elif response == "reboot":
            subprocess.run(["gnome-session-quit", "--reboot"])
            self.quit()
        elif response == "again":
            self.builder.get_object("runningStack").set_visible_child(
                self.builder.get_object("installationPage")
            )
            self.builder.get_object("installationBack").set_sensitive(False)
            self.builder.get_object("runningStack").set_visible_child(
                self.builder.get_object("runningBox")
            )
        dialog.destroy()

    def spawn_vte(self):
        self.builder.get_object("main_window").set_hide_on_close(True)
        self.vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ['HOME'],
            generate_bash_script(),
            None,  # Environmental Variables (envv)
            GLib.SpawnFlags.DEFAULT,  # Spawn Flags
            None, None,  # Child Setup
            -1,  # Timeout (-1 for indefinitely)
            None,  # Cancellable
            None,  # Callback
            None  # User Data
        )
        self.builder.get_object("installSpinner").start()

    def view_progress(self, button):
        self.builder.get_object("runningStack").set_visible_child(
            self.builder.get_object("vteBox")
        )
        self.builder.get_object("installationBack").set_sensitive(True)

    def get_widget_id(self, widget):
        return self.builder.get_object(widget)

    def reveal_app_list(self, page):
        self.builder.get_object("additionalProgramsStack").set_visible_child(
            self.builder.get_object(page)
        )
        self.builder.get_object("additionalProgramsBack").set_sensitive(True)

    def on_additionalProgramsBackClicked(self, button):
        self.builder.get_object("additionalProgramsStack").set_visible_child(
            self.builder.get_object("additionalProgramsCategories")
        )
        button.set_sensitive(False)

    def on_installationBackClicked(self, button):
        self.builder.get_object("runningStack").set_visible_child(
            self.builder.get_object("runningBox")
        )
        button.set_sensitive(False)

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
            response = requests.get("https://nmcheck.gnome.org/check_network_status.txt", timeout=5)
            if "NetworkManager is online" in response.text:
                GLib.idle_add(self.wait_for_internet_idle, "repoPage")
            elif response.status_code != 200:
                GLib.idle_add(self.wait_for_internet_idle, "internetBox")
        except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError):
            GLib.idle_add(self.wait_for_internet_idle, "internetBox")
        while not connected:
            try:
                response = requests.get("https://nmcheck.gnome.org/check_network_status.txt", timeout=3)
                if "NetworkManager is online" in response.text:
                    connected = True
            except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError):
                connected = False
        GLib.idle_add(lambda: self.quick_setup_stack.set_visible_child(
            self.builder.get_object("repoPage")
        ))

    def on_welcome_stack_switched(self, stack, page):
        if self.welcome_leaflet.get_can_unfold():
            self.welcome_leaflet.navigate(Adw.NavigationDirection.FORWARD)

    def on_welcome_leaflet_unfoldable(self, leaflet, folded):
        for button in welcome_sidebar_buttons:
            button.set_visible(leaflet.get_folded())
        self.builder.get_object("sidebar_headerbar").set_show_start_title_buttons(leaflet.get_folded())
        self.builder.get_object("sidebar_headerbar").set_show_end_title_buttons(leaflet.get_folded())

    def on_leaflet_unfold_button_visible(self, button):
        button.set_visible(self.welcome_leaflet.get_can_unfold())


@Gtk.Template(filename=_PACKAGE_FILE)
class Package(Adw.ActionRow):
    __gtype_name__ = "Package"
    package_name = None
    action_command = None
    action_extra = None
    icon_path = None
    internal_icon_name = None
    default = False
    actions_required_list = None
    button_group = None
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
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.icon_path, 32, 32, True
            )
            self.icon.set_from_pixbuf(pixbuf)
        if self.internal_icon_name is not None:
            self.icon.set_from_icon_name(self.internal_icon_name)
        if self.button_group is not None:
            if self.button_group not in package_groups:
                package_groups[self.button_group] = self.switch
            else:
                if package_groups[self.button_group] is not self.switch:
                    self.switch.set_group(package_groups[self.button_group])

    @Gtk.Template.Callback("toggle_package")
    def toggle_package(self, button):
        if button.get_active():
            if self.package_name is not None:
                quick_setup_packages.append(self.package_name)
            if self.action_command is not None:
                quick_setup_commands.append(self.action_command)
            if self.action_extra is not None:
                quick_setup_extras.append(self.action_extra)
                for package in packages:
                    package.check_actions()
        else:
            if self.package_name is not None:
                quick_setup_packages.remove(self.package_name)
            if self.action_command is not None:
                quick_setup_commands.remove(self.action_command)
            if self.action_extra is not None:
                quick_setup_extras.remove(self.action_extra)
                for package in packages:
                    package.check_actions()

    @GObject.Property(type=str)
    def package(self):
        return self.package_name

    @package.setter
    def package(self, name):
        self.package_name = name

    @GObject.Property(type=str)
    def command(self):
        return self.action_command

    @command.setter
    def command(self, name):
        self.action_command = name

    @GObject.Property(type=str)
    def action(self):
        return self.action_extra

    @action.setter
    def action(self, name):
        self.action_extra = name

    @GObject.Property(type=str)
    def group(self):
        return self.button_group

    @group.setter
    def group(self, name):
        self.button_group = name

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

    @GObject.Property(type=str)
    def actions_required(self):
        return self.actions_required_list

    @actions_required.setter
    def actions_required(self, actions):
        self.actions_required_list = actions.split(",")

    @Gtk.Template.Callback("check_actions")
    def check_actions(self, *args, **kwargs):
        if self.actions_required_list is not None:
            sensitive = True
            for action in self.actions_required_list:
                if action not in quick_setup_extras:
                    sensitive = False
            self.set_sensitive(sensitive)

            self.switch.set_active(False)
            if self.button_group is not None:
                if package_groups[self.button_group] is self.switch:
                    self.switch.set_active(True)

@Gtk.Template(filename=_LAUNCHER_FILE)
class Launcher(Adw.ActionRow):
    __gtype_name__ = "Launcher"
    launch_command = None
    icon_path = None
    internal_icon_name = None
    icon = Gtk.Template.Child("icon_image")
    button = Gtk.Template.Child("launch_button")

    def __init__(self):
        super().__init__(self)

    @Gtk.Template.Callback("on_update_defaults")
    def on_update_defaults(self, *args, **kwargs):
        if self.icon_path is not None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.icon_path, 32, 32, True
            )
            self.icon.set_from_pixbuf(pixbuf)
        if self.internal_icon_name is not None:
            self.icon.set_from_icon_name(self.internal_icon_name)

    @Gtk.Template.Callback("run_launcher")
    def run_launcher(self, button):
        subprocess.Popen(self.command)

    @GObject.Property(type=str)
    def command(self):
        return self.launch_command

    @command.setter
    def command(self, value):
        self.launch_command = value.split(" ")

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


@Gtk.Template(filename=_NAVIGATION_ROW_FILE)
class NavigationRow(Adw.ActionRow):
    __gtype_name__ = "NavigationRow"
    next_page_id = None
    previous_page_id = None
    stack_id = None
    back_btn = Gtk.Template.Child("back_btn")
    next_btn = Gtk.Template.Child("next_btn")
    start = False

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
        if self.next_page_id == "installationPage":
            application.builder.get_object("main_window").set_hide_on_close(True)
            application.spawn_vte()
            application.builder.get_object("installSpinner").start()


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

    @GObject.Property(type=bool, default=False)
    def start_button(self):
        return self.start

    @start_button.setter
    def start_button(self, start):
        self.start = start

    @Gtk.Template.Callback("on_start_changed")
    def on_start_changed(self, *args, **kwargs):
        if self.start:
            self.next_btn.set_label(_("Start"))
        else:
            self.next_btn.set_label(_("Next"))


@Gtk.Template(filename=_SIDEBAR_BUTTON_FILE)
class SidebarButton(Gtk.Button):
    __gtype_name__ = "SidebarButton"

    def __init__(self):
        super().__init__()
        welcome_sidebar_buttons.append(self)

    @Gtk.Template.Callback("on_click")
    def on_click(self, button):
        self.get_root().get_application().welcome_leaflet.navigate(Adw.NavigationDirection.BACK)

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


def generate_bash_script():
    script = ["#!/bin/bash"]
    for command in quick_setup_commands:
        script.append(command)
    for action in quick_setup_extras:
        script = script + actions[action]
    if quick_setup_packages is not None and quick_setup_packages != []:
        script.append(f"dnf install -y {' '.join(quick_setup_packages)}")
        script.append("echo Checking for installed packages...")
        for package in quick_setup_packages:
            script.append(f"rpm -q {package} || exit 1")
    script.append("touch /usr/share/risiWelcome/quick-setup-done")
    script.append("echo 'Done!'")

    bash_file_path = tempfile.mktemp(suffix=".sh", prefix="risiWelcome-")
    with open(bash_file_path, "w") as f:
        f.write("\n".join(script))
    print(bash_file_path)

    return ["/usr/bin/bash", _PW_PROMPTER, bash_file_path]

@Gtk.Template(filename=_TOUR_PAGE_FILE)
class TourPage(Gtk.Box):
    __gtype_name__ = "TourPage"
    _title = None
    _description = None
    filename = None
    label = Gtk.Template.Child("label")
    video = Gtk.Template.Child("video")

    @GObject.Property(type=str)
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

    @GObject.Property(type=str)
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @GObject.Property(type=str)
    def video(self):
        return self.filename

    @video.setter
    def video(self, filename):
        self.filename = os.path.dirname(os.path.abspath(__file__)) + f"/videos/{filename}"

    @Gtk.Template.Callback("on_update_defaults")
    def on_update_defaults(self, *args, **kwargs):
        self.label.set_label(self._description)
        self.video.set_from_filename(self.filename)


@Gtk.Template(filename=_TOUR_FILE)
class Tour(Gtk.Box):
    __gtype_name__ = "Tour"
    carousel = Gtk.Template.Child("carousel")
    back_btn = Gtk.Template.Child("back_btn")
    fw_btn = Gtk.Template.Child("fw_btn")
    headerlabel = Gtk.Template.Child("headerlabel")

    @Gtk.Template.Callback("on_forward")
    def on_forward(self, button):
        self.carousel.scroll_to(self.carousel.get_nth_page(self.carousel.get_position() + 1))

    @Gtk.Template.Callback("on_back")
    def on_back(self, button):
        self.carousel.scroll_to(self.carousel.get_nth_page(self.carousel.get_position() - 1))

    @Gtk.Template.Callback("on_page_changed")
    def on_page_changed(self, carousel, postiton, user_data):
        if carousel.get_position() == 0:
            self.back_btn.set_sensitive(False)
        elif carousel.get_position() == carousel.get_n_pages() - 1:
            self.fw_btn.set_sensitive(False)
        self.headerlabel.set_label(carousel.get_nth_page(carousel.get_position()).title())


if __name__ == "__main__":
    app = Application()
    app.run(None)