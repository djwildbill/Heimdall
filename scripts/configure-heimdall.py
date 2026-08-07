#!/usr/bin/env python3
import pathlib
import re
import sys

CONFIG = pathlib.Path('/etc/pwnagotchi/config.toml')

SETTINGS = {
    'main.name': '"heimdall"',
    'main.custom_plugins': '"/usr/local/share/pwnagotchi/custom-plugins"',
    # Preserve original Pwnagotchi-style active behavior as Heimdall's PWN mode.
    'personality.deauth': 'true',
    'personality.associate': 'true',
    'personality.advertise': 'true',
    'main.plugins.grid.enabled': 'false',
    'main.plugins.grid.report': 'false',
    'main.plugins.heimdall-mode.enabled': 'true',
    'main.plugins.heimdall-mode.default_mode': '"pwn"',
    'main.plugins.heimdall-mode.mode_path': '"/var/lib/heimdall/mode"',
    'main.plugins.heimdall-mode.poll_interval': '15',
    'main.plugins.heimdall-mode.timeout': '5',
    'main.plugins.heimdall-heartbeat.enabled': 'true',
    'main.plugins.heimdall-heartbeat.node_name': '"heimdall-01"',
    'main.plugins.heimdall-heartbeat.interval': '60',
    'main.plugins.heimdall-heartbeat.timeout': '5',
    'main.plugins.heimdall-heartbeat.interface': '"wlan0"',
    'main.plugins.heimdall-heartbeat.queue_path': '"/var/lib/heimdall/heartbeat-queue.jsonl"',
    'main.plugins.heimdall-health.enabled': 'true',
    'main.plugins.heimdall-health.interval': '60',
    'main.plugins.heimdall-health.status_path': '"/var/lib/heimdall/health.json"',
}

OPTIONAL_DEFAULTS = {
    'main.plugins.heimdall-mode.control_endpoint': '""',
    'main.plugins.heimdall-mode.token': '""',
    'main.plugins.heimdall-heartbeat.endpoint': '""',
    'main.plugins.heimdall-heartbeat.token': '""',
}


def set_key(text, key, value):
    pattern = re.compile(rf'(?m)^\s*{re.escape(key)}\s*=.*$')
    replacement = f'{key} = {value}'
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    if text and not text.endswith('\n'):
        text += '\n'
    return text + replacement + '\n'


def main():
    if not CONFIG.exists():
        print(f'{CONFIG} does not exist', file=sys.stderr)
        return 1

    text = CONFIG.read_text(encoding='utf-8')
    for key, value in SETTINGS.items():
        text = set_key(text, key, value)

    for key, value in OPTIONAL_DEFAULTS.items():
        pattern = re.compile(rf'(?m)^\s*{re.escape(key)}\s*=')
        if not pattern.search(text):
            text = set_key(text, key, value)

    CONFIG.write_text(text, encoding='utf-8')
    print('Heimdall configuration applied.')
    print('Default mode: PWN (original active behavior).')
    print('Available modes: pwn, sentinel, recon, maintenance.')
    print('Use active modes only in environments where you have authorization.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
