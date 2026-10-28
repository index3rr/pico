# Pico projects

My Pico projects: Wake-on-LAN, TCP forwarding, and USB keyboard/mouse control.
Each application has its own folder under `projects/`; shared modules and host
tools support the collection.

| Folder | Contents |
| --- | --- |
| [projects/wake_on_lan/](projects/wake_on_lan/README.md) | HTTP Wake-on-LAN application |
| [projects/tcp_proxy/](projects/tcp_proxy/README.md) | Asynchronous TCP forwarding application |
| [projects/usb_control/](projects/usb_control/README.md) | USB keyboard/mouse application, startup routing, and USB libraries |
| [shared/](shared/README.md) | Wi-Fi startup, webhook helper, and example credentials |
| `tools/` | Host commands for HID input, webcam capture, deployment, and serial maintenance |
| `plugins/` | Thonny bridge sharing the GUI's serial connection |
| `examples/` | Small diagnostic scripts |
| `tests/` | HTTP parser and input-validation tests |
| `docs/` | Control, deployment, and maintenance instructions |

## Host tools

Run `nix-shell` if you need the dependencies in `shell.nix`. From this directory:

```sh
python3 tools/hid.py status
python3 tools/hid.py key SEARCH RIGHT
python3 tools/webcam.py --warmup 60
```

The Pico's current address is `192.168.0.82`, control port `8765`. Plug it into an
awake USB host with a data cable to start keyboard/mouse control. Wall power
runs the preserved normal app after a ten-second USB detection window.

For serial maintenance, plug it into this computer and run `./thonny-pico`.
Opening Thonny stops the network control service while you use the REPL.

- [Keyboard/mouse control, webcam, and deployment](docs/control.md)
- [Thonny, file transfer, and watchdog recovery](docs/thonny.md)
- [Wake-on-LAN setup](projects/wake_on_lan/README.md)
- [TCP proxy setup](projects/tcp_proxy/README.md)

## Development

```sh
python3 -m unittest discover -s tests -v
```

USB control's dependencies are vendored with their license and pinned
upstream revision in [projects/usb_control/lib](projects/usb_control/lib/README.md). No pip installation
is needed. Local credentials, Thonny settings, snapshots, and board backups
remain in ignored `.thonny/`; keep that directory private and retain its backups.
