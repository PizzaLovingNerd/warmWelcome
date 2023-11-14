# Vendors Guide

There are two files to modify located in *module_path*/vendor.

- **distro_config.yml:** Contains the command for package installation and scripts for actions
- **welcome.xml:** GtkBuilder file with interface

# distro_config.yml
There are currently two config options for the config.

### install_command (string)
This is the command ran to install a package in your distro package manager (before the package name).
Make sure to enable some sort of no-confirm option.

examples:
- `dnf install -y`
- `apt install -y`

### actions (dictionary (strings))
This is a dictionary full of actions that your package rows can run. These actions are basically mini bash scripts.
Make sure to include the "script_base" action that is ran at the beginning of the script. We recommend a system update for script_base, but at the very least add a bash shabang (`#!/bin/bash`).

### first_page_after_welcome (string)
ID of page to switch to after the introduction page. This is needed because there is first an internet page that checks for wifi connection than navigates to this page.

yaml example:
```yaml
actions:
  script_base: |
    #!/bin/bash
    echo Updating System
    sudo dnf upgrade -y
  rpmfusion: |
    echo Installing RPMFusion Repositories
    dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
    echo Updating AppStream
    dnf groupupdate core -y --skip-broken
    echo Installing Multimedia Packages
    dnf swap -y ffmpeg-free ffmpeg --allowerasing
    dnf groupupdate multimedia -y --setop=\install_weak_deps=False\ --exclude=PackageKit-gstreamer-plugin --skip-broken
    echo Sound and Video Packages
    dnf groupupdate sound-and-video -y --skip-broken
  flatpak: |
    echo Installing Flatpak
    dnf install -y flatpak
    echo Adding Flathub
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    echo Adding Theme Overrides
    flatpak override --filesystem=~/.themes
    flatpak override --filesystem=xdg-config/gtk-4.0
    flatpak override --filesystem=xdg-config/gtk-3.0
```

# welcome.xml
This is the GtkBuilder UI file with the entire interface of the program. Vendors will probably want to edit this file.

## warmWelcome Row Widgets
We have a series of custom widgets you can use when building the UI out.

### Package
This is used to create a row for toggling a package in quick setup. Here are the properties available (all of these are optional):

- **package:** includes the package name, example: `firefox`
- **command:** bash command to run, example: `dnf config-manager --add-repo https://rpm.librewolf.net/librewolf-repo.repo`
- **action:** runs script for action defined in distro_config.yml, example: `rpmfusion`
- **group:** group packages together for giving users choice, example: `nvidia`
- **iconfile:** iconfile name. Store icons in *module_path*/icons/*iconfile*, example: `firefox.png`
- **iconname:** system icon name, example: `applications-graphics-symbolic`
- **switch-default:** if the package will be installed by default, example: `True`
- **prereqs-required:** if the package requires a prereq to be installed.
  - This can be any defined action that is enabled to be installed or
  - intel, amd, nvidia, based on GPU vendor
  - examples: `nvidia`, `rpmfusion`, `flatpak`
- All properties from [Adw.ActionRow](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ActionRow.html#properties) (aside from `icon_name`)


### Launcher
Used on the welcome screen area to launch a program or command. Here are the properties available:
- **command (REQUIRED):** bash command to run, example: `/usr/bin/xdg-open https://risi.io`
- **iconfile:** iconfile name. Store icons in *module_path*/icons/*iconfile*, example: `firefox.png`
- **iconname:** system icon name, example: `applications-graphics-symbolic`
- All properties from [Adw.ActionRow](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ActionRow.html#properties) (aside from `icon_name`)

### CategoryChooser
Used on quick setup to choose a category of packages to install. Here are the properties available:
- **page (REQUIRED):** page_id to switch to when category is selected, example: `videoProductionPage`
- **iconfile:** iconfile name. Store icons in *module_path*/icons/*iconfile*, example: `firefox.png`
- **iconname:** system icon name, example: `applications-graphics-symbolic
- All properties from [Adw.ActionRow](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ActionRow.html#properties) (aside from `icon_name`)

### NavigationRow
Used for switching between pages on Quick Setup. Here are the properties available:
- **next-page:** page_id to switch to on next button, exmaple: `browserPage`
- **previous-page:** page_id to switch to on back button, exmaple: `welcomeBox`
- **stack:** stack id that the row edits, example: `quickSetupStack`

## warmWelcome other widgets
These are widgets that you likely won't need if you are editing the existing welcome.xml file which is the recommended way to go.

### SidebarButton
This is simply a button that shows the sidebar if the sidebar is hidden (for adaptive windows). This button has no properties.

# Editing welcome.xml
You likely want to edit the existing welcome.xml. Here is a guide for elements down below. You can also search for `<!--EDIT THIS-->`
This assumes you know how to edit a Gtk.Builder XML file and are familiar with GTK4.

## Tips:
- If creating or rearranging pages in Quick Setup, make sure to edit the page's NavigationRow's next-page and previous-page properties to match the new page ids.
- Every Quick Setup page aside from the intro and internet page should be structured like this:
  - GtkBox
    - AdwHeaderBar
    - AdwPreferencesPage
      - AdwPreferencesGroup (can have more than one)
        - Adw.ActionRow (can have more than one, refer to Package, NavigationRow, and CategoryChooser widgets)
- The Welcome Screen is laid out like this
  - GtkStack (welcomeStack)
    - GtkStackPage
      - AdwHeaderBar (SidebarButton to start, add Label for title)
      - AdwPreferencesPage
        - AdwPreferencesGroup (can have more than one)
          - Adw.ActionRow (can have more than one, refer to Launcher widget)

## Elements:
  Here is a list of important elements in the welcome.xml file. BOLD means you may want to edit this area.:
  - mainStack: This stack holds two pages.
    - quickSetupStack: Holds quick setup pages
      - **welcomeBox:** Info for distribution. Edit your distro name within the AdwStatusPage.
      - internetBox: Used for checking internet connection. We recommend not editing this.
      - **repoPage:** Fedora specific options, edit this category for your distro.
      - **browserPage:** Page to select browsers. Edit this for your distro's packages.
      - **driverPage:** Page to select drivers. Edit this for your distro's packages.
      - **additionalProgramsPage:** Page to select additional programs. Full of other categories.
        - **audioConsumptionPage:** Page to select audio consumption programs. Edit this for your distro's packages.
        - **audioProductionPage:** Page to select audio production programs. Edit this for your distro's packages.
        - **gamingPage:** Page to select gaming programs. Edit this for your distro's packages.
        - **graphicsPage:** Page to select graphics programs. Edit this for your distro's packages.
        - **videoProductionPage:** Page to select video production programs. Edit this for your distro's packages.
      - installationPage: Used for running the installation script. We recommend not editing this.
    - welcomeLeaflet: Holds welcome screen
      - **sidebar_headerbar:** Headerbar for sidebar. Edit this for your distro's name.
      - **welcomeStack: We recommend completely customizing every page in here for your distro.**