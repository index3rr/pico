#!/usr/bin/env python3
"""Control the Pico through the repo's running Thonny instance (stdlib only)."""
import argparse
import configparser
import json
import os
from pathlib import Path
import socket
import sys
import time

WATCHDOG_LINE = "    wdt = machine.WDT(timeout=8000)"
WATCHDOG_DEVELOPMENT = """    # A hardware watchdog survives Ctrl-C and resets the USB connection.
    # Keep it disabled during development; remove the marker and hard-reset
    # the board to restore watchdog protection for standalone use.
    import os
    try:
        os.stat('/.pico-development')
        wdt = None
    except OSError:
        wdt = machine.WDT(timeout=8000)"""

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".thonny"


def configure():
    STATE.mkdir(mode=0o700, exist_ok=True)
    config_path = STATE / "configuration.ini"
    if (STATE / "control.sock").exists():
        try:
            call("status")
            return
        except OSError:
            pass
    ports = sorted(Path("/dev/serial/by-id").glob("usb-MicroPython*"))
    port = os.environ.get("PICO_PORT")
    if not port and len(ports) == 1:
        port = str(ports[0])
    if not port:
        raise RuntimeError("Set PICO_PORT to the board's /dev/serial/by-id/... path")
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path)
    for section in ("general", "run", "RPiPico", "view"):
        if not config.has_section(section):
            config.add_section(section)
    config["general"]["single_instance"] = "True"
    config["run"]["backend_name"] = "RPiPico"
    config["RPiPico"].update(port=port, interrupt_on_connect="True", sync_time="False")
    config["view"]["filesview.visible"] = "True"
    with config_path.open("w") as f:
        config.write(f)


def call(action, **kwargs):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(kwargs.get("timeout", 30) + 5)
        client.connect(str(STATE / "control.sock"))
        client.sendall(json.dumps(dict(action=action, **kwargs)).encode() + b"\n")
        with client.makefile("rb") as f:
            line = f.readline()
        if not line:
            raise RuntimeError("Thonny closed the connection")
        result = json.loads(line)
        if not result["ok"]:
            raise RuntimeError(result.get("error") or result.get("stderr") or "Command failed")
        return result


def execute(source, timeout=30):
    return call("exec", source=source, timeout=timeout).get("stdout", "")


def read_remote(path):
    # Tagged output avoids treating unrelated program output as file contents.
    output = execute("import binascii, gc\ngc.collect()\nwith open(%r, 'rb') as _pico_file:\n while True:\n  _pico_chunk = _pico_file.read(512)\n  if not _pico_chunk:\n   break\n  print('PICO_FILE:' + binascii.hexlify(_pico_chunk).decode())\nprint('PICO_FILE_END')" % path)
    chunks = []
    for line in output.splitlines():
        if line.startswith("PICO_FILE:"):
            chunks.append(bytes.fromhex(line[len("PICO_FILE:"):]))
    if 'PICO_FILE_END' not in output.splitlines():
        raise RuntimeError("Incomplete file data received")
    return b''.join(chunks)


def put(local, remote):
    data = Path(local).read_bytes()
    # Write and verify a temporary file before replacing the destination.
    temporary = remote + ".pico-upload"
    execute("import binascii, os, gc\nwith open(%r, 'wb') as _pico_file:\n pass" % temporary)
    for offset in range(0, len(data), 1024):
        execute("gc.collect()\nwith open(%r, 'ab') as _pico_file:\n _pico_file.write(binascii.unhexlify(%r))" % (temporary, data[offset:offset + 1024].hex()))
    if read_remote(temporary) != data:
        raise RuntimeError("Upload verification failed; destination was not replaced")
    execute("os.rename(%r, %r)" % (temporary, remote))
    print("Uploaded and verified %s (%d bytes)" % (remote, len(data)))


def development(enabled):
    # Dual-mode installations preserve the original app under this name.
    listing = execute("import os; print('NORMAL_APP:' + str('normal_main.py' in os.listdir('/')))")
    remote_main = '/normal_main.py' if 'NORMAL_APP:True' in listing else '/main.py'
    if enabled:
        source = read_remote(remote_main).decode()
        if WATCHDOG_DEVELOPMENT not in source:
            if source.count(WATCHDOG_LINE) != 1:
                raise RuntimeError("Unrecognized watchdog setup; inspect main.py before patching")
            backup = STATE / 'backups' / time.strftime('%Y%m%d-%H%M%S')
            backup.mkdir(parents=True, mode=0o700)
            for name in ('boot.py', 'main.py', 'oldmain.py', 'webhook.py'):
                (backup / name).write_bytes(read_remote('/' + name))
            patched = STATE / 'main-watchdog-development.py'
            patched.write_text(source.replace(WATCHDOG_LINE, WATCHDOG_DEVELOPMENT))
            put(patched, remote_main)
            print('Original scripts backed up to', backup)
        execute("with open('/.pico-development', 'w') as _pico_marker:\n _pico_marker.write('Watchdog disabled for Thonny development\\n')")
    else:
        execute("import os\ntry:\n os.remove('/.pico-development')\nexcept OSError:\n pass")
    print('Development mode %s. Hard-reset or unplug/replug the Pico to apply.' % ('enabled' if enabled else 'disabled'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("configure", "status", "interrupt", "reconnect", "info", "ls"):
        sub.add_parser(action)
    p = sub.add_parser("exec")
    p.add_argument("source")
    p.add_argument("--timeout", type=float, default=30)
    p = sub.add_parser("run")
    p.add_argument("file")
    p.add_argument("--timeout", type=float, default=30)
    p = sub.add_parser("put")
    p.add_argument("local")
    p.add_argument("remote")
    p = sub.add_parser("get")
    p.add_argument("remote")
    p.add_argument("local")
    p = sub.add_parser("health")
    p.add_argument("--seconds", type=float, default=120)
    p.add_argument("--interval", type=float, default=2)
    p = sub.add_parser("development", help="Toggle the installed application's watchdog for editing")
    p.add_argument("mode", choices=("on", "off"))
    args = parser.parse_args()
    if args.command == "configure":
        configure()
    elif args.command in ("status", "interrupt", "reconnect"):
        print(json.dumps(call(args.command), indent=2))
    elif args.command == "info":
        print(execute("import os, sys, machine, binascii\nprint(os.uname())\nprint(sys.implementation)\nprint('Board ID:', binascii.hexlify(machine.unique_id()).decode())\nprint('Files:', os.listdir('/'))"), end="")
    elif args.command == "ls":
        print(execute("import os\nprint(os.listdir('/'))"), end="")
    elif args.command == "exec":
        print(execute(args.source, args.timeout), end="")
    elif args.command == "run":
        source = "exec(compile(%r, %r, 'exec'))" % (Path(args.file).read_text(), args.file)
        print(execute(source, args.timeout), end="")
    elif args.command == "put":
        put(args.local, args.remote)
    elif args.command == "development":
        development(args.mode == "on")
    elif args.command == "get":
        destination = Path(args.local)
        data = read_remote(args.remote)
        # Avoid accidentally overwriting a local script or backup.
        with destination.open("xb") as f:
            f.write(data)
        print("Downloaded %d bytes to %s" % (len(data), destination))
    elif args.command == "health":
        if args.seconds <= 0 or args.interval <= 0:
            raise ValueError("seconds and interval must be positive")
        start, count = time.monotonic(), 0
        while time.monotonic() - start < args.seconds:
            expected = "PICO_HEALTH_%d" % count
            if expected not in execute("print(%r)" % expected):
                raise RuntimeError("Missing health response")
            count += 1
            print("%0.1fs: response %d OK" % (time.monotonic() - start, count), flush=True)
            time.sleep(args.interval)
        print("PASS: %d round trips over %.1fs, no reconnects" % (count, time.monotonic() - start))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        print("pico: %s" % exc, file=sys.stderr)
        sys.exit(1)
