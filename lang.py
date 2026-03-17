"""
Internationalization module for wireguard-tray.

Usage:
    from lang import t
    t("vpn_on")  # Returns translated string for current language

To configure language, set WIREGUARD_TRAY_LANG environment variable
or create ~/.config/wireguard-tray/lang file with language code (e.g. "en" or "ru").
"""

import os

TRANSLATIONS = {
    "en": {
        "vpn_on": "VPN enabled",
        "vpn_off": "VPN disabled",
        "connected": "Connected: {iface}",
        "disconnected": "Disconnected: {iface}",
        "connection_error": "Connection error",
        "disconnection_error": "Disconnection error",
        "interface_selected": "Interface selected: {iface}",
        "no_access": "No access to /etc/wireguard",
        "interface": "Interface",
        "exit": "Exit",
        "run_with_sudo": "Run this flag with sudo!",
        "sudoers_configured": "Sudoers and permissions for /etc/wireguard configured for {user}",
    },
    "ru": {
        "vpn_on": "VPN включён",
        "vpn_off": "VPN выключен",
        "connected": "Подключён: {iface}",
        "disconnected": "Отключён: {iface}",
        "connection_error": "Ошибка подключения",
        "disconnection_error": "Ошибка отключения",
        "interface_selected": "Выбран интерфейс: {iface}",
        "no_access": "Нет доступа к /etc/wireguard",
        "interface": "Интерфейс",
        "exit": "Выход",
        "run_with_sudo": "Запустите этот флаг с sudo!",
        "sudoers_configured": "Sudoers и права на /etc/wireguard настроены для {user}",
    },
}

DEFAULT_LANG = "en"


def _detect_language():
    """Detect language from env var, config file, or system locale."""
    env_lang = os.getenv("WIREGUARD_TRAY_LANG")
    if env_lang and env_lang in TRANSLATIONS:
        return env_lang

    config_dir = os.path.join(os.path.expanduser("~/.config"), "wireguard-tray")
    lang_file = os.path.join(config_dir, "lang")
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
    """Get translated string by key, with optional format arguments."""
    text = TRANSLATIONS.get(_current_lang, TRANSLATIONS[DEFAULT_LANG]).get(
        key, TRANSLATIONS[DEFAULT_LANG].get(key, key)
    )
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_language():
    """Return current language code."""
    return _current_lang


def available_languages():
    """Return list of available language codes."""
    return list(TRANSLATIONS.keys())
