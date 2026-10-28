# Thonny maintenance

Plug the Pico into this NixOS computer, close competing serial connections, and
start the repo profile:

```sh
./thonny-pico
```

The launcher discovers one MicroPython board through `/dev/serial/by-id/`.
For multiple boards, set `PICO_PORT` to the desired by-id path before launching.
The local plugin shares Thonny's existing backend through a user-only Unix
socket; automation never opens a competing serial connection. Personal Thonny
settings stay separate in the regular user profile.

Opening the REPL interrupts the Pico's application and stops its HTTP control
service. Use the network client in [control.md](control.md) when serial access
is unnecessary. Close Thonny and power-cycle the Pico to resume automatic startup.

## Commands

With the repo's Thonny window open, use another terminal:

```sh
python3 tools/pico.py status
python3 tools/pico.py info
python3 tools/pico.py ls
python3 tools/pico.py exec "print('hello from the Pico')"
python3 tools/pico.py run examples/connection_check.py
python3 tools/pico.py put examples/connection_check.py /connection_check.py
python3 tools/pico.py get /connection_check.py /tmp/connection_check-backup.py
python3 tools/pico.py health --seconds 120
python3 tools/pico.py interrupt
python3 tools/pico.py reconnect
```

`run` executes without saving. `put` uploads in small chunks, verifies the
complete temporary file, then renames it over the destination. `get` refuses
to overwrite a local file. Output also appears in Thonny's Shell.

Use `--timeout 120` with `run` or `exec` for longer commands. A timeout does not
stop code or retry it. Interrupt and inspect the board before repeating a
command whose effects are uncertain.

## Watchdog and USB resets

The installed standalone app uses an eight-second hardware watchdog. Once
started, it survives Ctrl-C and resets the board when the program stops feeding
it, dropping the USB connection. A hard reset is needed to clear it.

The app checks for `/.pico-development` before enabling its watchdog. The marker
is currently present, keeping the watchdog disabled during editing. USB control
mode never enables a watchdog. To restore standalone watchdog protection:

```sh
python3 tools/pico.py development off
```

Close Thonny and power-cycle. Before future editing, enable development mode
shortly after connecting, then power-cycle and reconnect:

```sh
python3 tools/pico.py development on
```

On dual-mode installations, this command targets `/normal_main.py`. It backs
up recognized unpatched watchdog code before changing it and refuses unknown
watchdog setups. Board backups are under `.thonny/backups/`.

The Thonny plugin also handles by-id symlinks when looking up the port in the
GUI. Initializing or resetting runtime USB HID interfaces intentionally causes
USB re-enumeration. Persistent USB protocol errors can still require checking
the cable and port.

References: [MicroPython watchdog](https://docs.micropython.org/en/v1.28.0/library/machine.WDT.html),
[USB device lifecycle](https://docs.micropython.org/en/latest/library/machine.USBDevice.html).
