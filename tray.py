#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, AppIndicator3

APP_NAME = "wireguard-tray"

ICON_DIR = "/usr/share/wireguard-tray/icons"
ICON_OFF = os.path.join(ICON_DIR, "icon-off.png")
ICON_ON = os.path.join(ICON_DIR, "icon-on.png")

CONFIG_DIR = os.path.join(os.path.expanduser("~/.config"), APP_NAME)
WG_CONFIG_DIR = "/etc/wireguard"
WG_QUICK = "/usr/bin/wg-quick"

TRANSLATIONS = {
    "en": {
        "vpn_off": "VPN disabled",
        "connected": "Connected: {iface}",
        "disconnected": "Disconnected: {iface}",
        "connection_error": "Connection error",
        "disconnection_error": "Disconnection error",
        "no_configs": "No configs found in /etc/wireguard",
        "exit": "Exit",
        "run_with_sudo": "Run this flag with sudo!",
        "sudoers_configured": (
            "Sudoers and permissions for /etc/wireguard configured for {user}"
        ),
    },
    "ru": {
        "vpn_off": "VPN выключен",
        "connected": "Подключён: {iface}",
        "disconnected": "Отключён: {iface}",
        "connection_error": "Ошибка подключения",
        "disconnection_error": "Ошибка отключения",
        "no_configs": "Конфигурации не найдены в /etc/wireguard",
        "exit": "Выход",
        "run_with_sudo": "Запустите этот флаг с sudo!",
        "sudoers_configured": (
            "Sudoers и права на /etc/wireguard настроены для {user}"
        ),
    },
}
DEFAULT_LANG = "en"


def _detect_language():
    env_lang = os.getenv("WIREGUARD_TRAY_LANG")
    if env_lang and env_lang in TRANSLATIONS:
        return env_lang
    lang_file = os.path.join(CONFIG_DIR, "lang")
    if os.path.exists(lang_file):
        with open(lang_file, "r") as f:
            lang = f.read().strip()
            if lang in TRANSLATIONS:
                return lang
    sys_lang = os.getenv("LANG", "")
    for code in TRANSLATIONS:
        if sys_lang.startswith(code):
            return code
    return DEFAULT_LANG


_current_lang = _detect_language()


def t(key, **kwargs):
    text = TRANSLATIONS.get(_current_lang, TRANSLATIONS[DEFAULT_LANG]).get(
        key, TRANSLATIONS[DEFAULT_LANG].get(key, key)
    )
    if kwargs:
        text = text.format(**kwargs)
    return text


indicator = None
active_interfaces = set()


def notify(title, message, icon=ICON_OFF):
    subprocess.Popen(
        ["notify-send", "-i", icon, title, message],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _config_path(iface):
    return os.path.join(WG_CONFIG_DIR, f"{iface}.conf")


def run_wg(action, iface):
    """Returns True on success, False on failure."""
    cmd = ["sudo", WG_QUICK, action, _config_path(iface)]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if action == "up" and "already exists" in stderr:
            return True
        if action == "down" and "not found" in stderr:
            return True
        print(f"wg-quick {action} {iface}: {result.stderr.strip()}")
        return False
    return True


def _is_valid_config(config_text):
    return "[Interface]" in config_text


def get_available_interfaces():
    result = subprocess.run(
        ["sudo", "ls", WG_CONFIG_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return []
    interfaces = []
    for f in sorted(result.stdout.splitlines()):
        if not f.endswith(".conf"):
            continue
        iface = f[:-5]
        check = subprocess.run(
            ["sudo", "cat", _config_path(iface)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if check.returncode == 0 and _is_valid_config(check.stdout):
            interfaces.append(iface)
    return interfaces


def get_active_interfaces():
    result = subprocess.run(
        ["sudo", "wg", "show", "interfaces"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return set(result.stdout.strip().split())
    return set()


def update_icon():
    if active_interfaces:
        indicator.set_icon_full(ICON_ON, "VPN active")
        label = ", ".join(sorted(active_interfaces))
        indicator.set_label(label, "")
    else:
        indicator.set_icon_full(ICON_OFF, "VPN inactive")
        indicator.set_label(t("vpn_off"), "")


def on_toggle_interface(item, iface):
    if item.get_active():
        if run_wg("up", iface):
            active_interfaces.add(iface)
            notify("WireGuard", t("connected", iface=iface), ICON_ON)
        else:
            item.handler_block_by_func(on_toggle_interface)
            item.set_active(False)
            item.handler_unblock_by_func(on_toggle_interface)
            notify("WireGuard", t("connection_error"))
    else:
        if run_wg("down", iface):
            active_interfaces.discard(iface)
            notify("WireGuard", t("disconnected", iface=iface))
        else:
            item.handler_block_by_func(on_toggle_interface)
            item.set_active(True)
            item.handler_unblock_by_func(on_toggle_interface)
            notify("WireGuard", t("disconnection_error"))
    update_icon()


def create_tray():
    global indicator, active_interfaces
    active_interfaces = get_active_interfaces()
    available = get_available_interfaces()

    indicator = AppIndicator3.Indicator.new(
        APP_NAME,
        ICON_OFF,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()

    if available:
        for iface in available:
            item = Gtk.CheckMenuItem(label=iface)
            item.set_active(iface in active_interfaces)
            item.connect("toggled", on_toggle_interface, iface)
            menu.append(item)
    else:
        no_configs = Gtk.MenuItem(label=t("no_configs"))
        no_configs.set_sensitive(False)
        menu.append(no_configs)

    menu.append(Gtk.SeparatorMenuItem())
    quit_item = Gtk.MenuItem(label=t("exit"))
    quit_item.connect("activate", Gtk.main_quit)
    menu.append(quit_item)
    menu.show_all()
    indicator.set_menu(menu)
    update_icon()


def handle_cli():
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("-a", "--autostart", action="store_true", help="Enable autostart")
    parser.add_argument(
        "-d", "--disable-autostart", action="store_true", help="Disable autostart"
    )
    parser.add_argument(
        "-u", "--up", metavar="IFACE", nargs="+", help="Bring interface(s) up and exit"
    )
    parser.add_argument(
        "-D", "--down", metavar="IFACE", nargs="+", help="Bring interface(s) down and exit"
    )
    parser.add_argument(
        "-s", "--sudo-setup", action="store_true", help="Setup sudoers for WireGuard"
    )
    parser.add_argument("-v", "--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print("wireguard-tray 1.0.0")
        sys.exit(0)

    if args.autostart:
        subprocess.run(["systemctl", "--user", "enable", "--now", "wireguard-tray"])
        print("Autostart enabled")
        sys.exit(0)

    if args.disable_autostart:
        subprocess.run(["systemctl", "--user", "disable", "--now", "wireguard-tray"])
        print("Autostart disabled")
        sys.exit(0)

    if args.up:
        failed = any(not run_wg("up", iface) for iface in args.up)
        sys.exit(1 if failed else 0)

    if args.down:
        failed = any(not run_wg("down", iface) for iface in args.down)
        sys.exit(1 if failed else 0)

    if args.sudo_setup:
        if os.geteuid() != 0:
            print(t("run_with_sudo"))
            sys.exit(1)
        user = os.getenv("SUDO_USER") or os.getenv("USER")
        sudoers_file = "/etc/sudoers.d/wireguard-tray"
        rules = [
            f"{user} ALL=(root) NOPASSWD: /usr/bin/wg-quick",
            f"{user} ALL=(root) NOPASSWD: /usr/bin/wg",
            f"{user} ALL=(root) NOPASSWD: /usr/bin/ls {WG_CONFIG_DIR}",
            f"{user} ALL=(root) NOPASSWD: /usr/bin/cat {WG_CONFIG_DIR}/*",
            f"{user} ALL=(root) NOPASSWD: /usr/bin/ip",
            f"{user} ALL=(root) NOPASSWD: /usr/bin/resolvectl",
            f"{user} ALL=(root) NOPASSWD: /usr/bin/resolvconf",
        ]
        with open(sudoers_file, "w") as f:
            f.write("\n".join(rules) + "\n")
        os.chmod(sudoers_file, 0o440)
        os.chmod("/etc/wireguard", 0o750)
        print(t("sudoers_configured", user=user))
        sys.exit(0)


def main():
    handle_cli()
    create_tray()
    Gtk.main()


if __name__ == "__main__":
    main()
