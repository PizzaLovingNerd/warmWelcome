Name:           risi-welcome
Version:        38.0
Release:        26%{?dist}
Summary:        risiOS's Welcome app.

License:        GPL v3
URL:            https://github.com/risiOS/risi-welcome
Source0:        https://github.com/risiOS/risi-welcome/archive/refs/heads/main.tar.gz

BuildArch:	noarch

BuildRequires:  python3
Requires:       python3
Requires:	python3-gobject
Requires:   lshw

%description
This welcome program will help guide you through the
available resources for risiOS as well as help you setup
your computer to your likings.

%prep
%autosetup -n %{name}-main

%build
%install

mkdir -p %{buildroot}%{_bindir}
cp -a usr/share %{buildroot}%{_datadir}
mkdir -p %{buildroot}%{_sysconfdir}/xdg/autostart/
cp usr/share/applications/io.risi.Welcome.desktop %{buildroot}%{_sysconfdir}/xdg/autostart/

cat > risi-welcome <<EOF
#!/bin/sh
/env/bin/python3 %{_datadir}/risiWelcome/__main__.py
EOF
install risi-welcome 775 %{buildroot}%{_bindir}

%files
%{_datadir}/risiWelcome
%{_datadir}/glib-2.0/schemas/io.risi.Welcome.gschema.xml
%{_datadir}/applications/io.risi.Welcome.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.risi.Welcome.svg
%{_bindir}/risi-welcome
%{_sysconfdir}/xdg/autostart/io.risi.Welcome.desktop

%changelog
* Fri Apr 28 2023 PizzaLovingNerd
- Redesign of the welcome app.

* Fri Sep 2 2022 PizzaLovingNerd
- Changed version scheme to match the distro release.

* Tue Mar 1 2022 PizzaLovingNerd
- First spec file
