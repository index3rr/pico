#!/usr/bin/env python3
"""Send explicit input commands to the Pico over the LAN. Never retries input."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent.parent


def request(path, data=None, url=None):
    token = os.environ.get('PICO_HID_TOKEN')
    if not token:
        token = (ROOT / '.thonny/hid-token').read_text().strip()
    base = url or os.environ.get('PICO_HID_URL', 'http://192.168.0.82:8765')
    payload = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base.rstrip('/') + path, data=payload,
                                 headers={'Authorization': 'Bearer ' + token,
                                          'Content-Type': 'application/json'})
    # Ignore proxy env vars for the local hardware control connection.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=20) as result:
            return json.load(result)
    except urllib.error.HTTPError as exc:
        try:
            message = json.load(exc).get('error', str(exc))
        except (ValueError, OSError):
            message = str(exc)
        raise RuntimeError(message) from exc


def actions(commands, url=None, command_id=None):
    return request('/api/actions', dict(id=command_id or uuid.uuid4().hex, actions=commands), url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Default: http://192.168.0.82:8765')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('wake', help='Request USB wakeup without sending keyboard input')
    sub.add_parser('release')
    p = sub.add_parser('type', help='Type text using a US keyboard layout')
    p.add_argument('text')
    p = sub.add_parser('key', help='Press and release a chord, e.g. CTRL ALT Z')
    p.add_argument('keys', nargs='+')
    p = sub.add_parser('move', help='Relative mouse movement')
    p.add_argument('dx', type=int)
    p.add_argument('dy', type=int)
    p = sub.add_parser('click')
    p.add_argument('button', nargs='?', default='left', choices=('left', 'right', 'middle'))
    p = sub.add_parser('scroll')
    p.add_argument('amount', type=int)
    p = sub.add_parser('batch', help='JSON file containing a list of action objects')
    p.add_argument('file')
    args = parser.parse_args()
    if args.command == 'status':
        result = request('/api/status', url=args.url)
    elif args.command == 'wake':
        result = request('/api/wake', {}, args.url)
    elif args.command == 'release':
        result = request('/api/release', {}, args.url)
    else:
        if args.command == 'batch':
            commands = json.loads(Path(args.file).read_text())
        else:
            command = dict(type={'type': 'text'}.get(args.command, args.command))
            for key in ('text', 'keys', 'dx', 'dy', 'button', 'amount'):
                if hasattr(args, key):
                    command[key] = getattr(args, key)
            commands = [command]
        result = actions(commands, args.url)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print('hid: %s. Input was not retried; inspect the screen before repeating.' % exc, file=sys.stderr)
        sys.exit(1)
