PREFIX ?= /usr
DESTDIR ?=

BINDIR = $(DESTDIR)$(PREFIX)/bin
SHAREDIR = $(DESTDIR)$(PREFIX)/share/wireguard-tray
ICONDIR = $(SHAREDIR)/icons
APPDIR = $(DESTDIR)$(PREFIX)/share/applications
SERVICEDIR = $(DESTDIR)$(PREFIX)/lib/systemd/user

.PHONY: install uninstall

install:
	install -Dm755 tray.py $(BINDIR)/wireguard-tray
	install -dm755 $(ICONDIR)
	install -Dm644 icon-off.png $(ICONDIR)/icon-off.png
	install -Dm644 icon-on.png $(ICONDIR)/icon-on.png
	install -Dm644 wireguard-tray.service $(SERVICEDIR)/wireguard-tray.service
	install -Dm644 wireguard-tray.desktop $(APPDIR)/wireguard-tray.desktop

uninstall:
	rm -f $(BINDIR)/wireguard-tray
	rm -rf $(SHAREDIR)
	rm -f $(SERVICEDIR)/wireguard-tray.service
	rm -f $(APPDIR)/wireguard-tray.desktop
