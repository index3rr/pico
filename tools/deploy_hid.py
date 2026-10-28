#!/usr/bin/env python3
"""Preserve installed applications and install dual-mode USB control via Thonny."""
import ast
import os
import time

import pico


def deploy():
    if not pico.call('status')['ready']:
        raise RuntimeError('Thonny must be connected with an idle Pico REPL')
    source = pico.ROOT / 'projects' / 'usb_control'
    backup = pico.STATE / 'backups' / ('before-hid-' + time.strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True, mode=0o700)
    # Only list files; never fetch or display secrets.py.
    listing = pico.execute("import os; print('FILES:' + repr(os.listdir('/')))")
    names = ast.literal_eval(next(line[6:] for line in listing.splitlines() if line.startswith('FILES:')))
    for name in ('boot.py', 'main.py', 'webhook.py', 'oldmain.py', 'normal_boot.py', 'normal_main.py'):
        if name in names:
            (backup / name).write_bytes(pico.read_remote('/' + name))
    if 'normal_main.py' not in names and 'normal_boot.py' not in names:
        pico.put(backup / 'boot.py', '/normal_boot.py')
        pico.put(backup / 'main.py', '/normal_main.py')
    elif 'normal_main.py' not in names or 'normal_boot.py' not in names:
        raise RuntimeError('Incomplete normal application backup on device; inspect before proceeding')
    token_path = pico.STATE / 'hid-token'
    if not token_path.exists():
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(os.urandom(32).hex() + '\n')
    token = token_path.read_text().strip()
    config = pico.STATE / 'hid_config.py'
    config.write_text('TOKEN = %r\nPORT = 8765\n' % token)
    config.chmod(0o600)
    pico.execute("import os\nfor _dir in ('/lib', '/lib/usb', '/lib/usb/device'):\n try:\n  os.mkdir(_dir)\n except OSError:\n  os.stat(_dir)")
    for f in sorted((source / 'lib/usb/device').glob('*.py')):
        pico.put(f, '/lib/usb/device/' + f.name)
    for name in ('pico_usb.py', 'hid_protocol.py', 'hid_server.py'):
        pico.put(source / name, '/' + name)
    pico.put(config, '/hid_config.py')
    # Write the entrypoints only once everything they import is installed.
    pico.put(source / 'main.py', '/main.py')
    pico.put(source / 'boot.py', '/boot.py')
    print('Installed. Original application preserved as /normal_boot.py and /normal_main.py.')
    print('Local backup:', backup)
    print('Token stored privately in .thonny/hid-token. Hard-reset the Pico to start.')


if __name__ == '__main__':
    deploy()
