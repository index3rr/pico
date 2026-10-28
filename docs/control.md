# Automatic USB keyboard/mouse control

The installed Pico W now selects its application after every power cycle:

| Connection | Behavior |
| --- | --- |
| Any active USB data host | USB keyboard + three-button mouse + wheel; authenticated HTTP control on port 8765 |
| Wall USB charger / power-only connection | Wait up to 10 seconds for USB enumeration, then run the preserved normal app |

The detector observes whether a USB host actually configures the HID interface;
USB power alone is insufficient. The detector cannot identify a particular host.
A sleeping/off computer, charge-only cable, or blocked USB interface can look
like a wall charger. Connect to an awake computer with a data cable. If the
host only starts later, unplug/replug the Pico to select control mode again.

No keys, mouse movements, or clicks are emitted automatically at startup. The
standard USB HID interfaces work without installing software on the host.

## Use from this NixOS computer

The Pico's verified LAN address is **192.168.0.82**. The code uses its existing
Wi-Fi credentials and DHCP; reserve that address on the router to keep it fixed.
Connect this computer to a network that can reach the Pico, plug the Pico into
the target computer, and wait for Wi-Fi to connect. Then:

```sh
python3 tools/hid.py status
python3 tools/hid.py wake
python3 tools/hid.py type 'Hello from the Pico'
python3 tools/hid.py key CTRL ALT Z
python3 tools/hid.py key SEARCH RIGHT
python3 tools/hid.py move 100 -50
python3 tools/hid.py click left
python3 tools/hid.py scroll -3
python3 tools/hid.py release
```

`SEARCH` / `LAUNCHER` map to the keyboard's left GUI key. The host operating
system determines the resulting behavior. Text currently assumes a **US keyboard layout** and
supports printable ASCII, newline, and tab. Each key/chord and click releases
automatically. Mouse movement is relative. There are no indefinite key holds.
`batch FILE.json` accepts a JSON list of `text`, `key`, `move`, `click`, `scroll`,
and `wait` actions. A batch must contain at most 32 actions and at most ten
seconds of requested typing/wait delays. An entire batch is validated before
any input is sent.

The service is HTTP on the trusted LAN, protected by a random bearer token in
ignored `.thonny/hid-token` locally and `/hid_config.py` on the Pico. The host
client reads it automatically. It is not an Internet-facing service; HTTP does
not encrypt the token. Clients can override `PICO_HID_URL` and `PICO_HID_TOKEN`.
There is no network Python evaluation endpoint. No token is stored in tracked
source files. `secrets.py` on the Pico is not modified or downloaded.

`wake` requests USB remote wakeup without sending keys. It requires the Pico
firmware with `/api/wake` support and the host enabling USB wake for the device.
`remote_wakeup_sent: true` means the Pico signalled resume; confirm the screen
before sending input. False can mean the host is already awake or did not enable
wakeup. `usb_ready` reports configured HID interfaces, not whether the host is
currently polling them; a suspended host can still report true and reject input.
Input is never replayed automatically after a wake request.

Deployment status: remote wakeup has been added to repository sources but has
not yet been installed or verified on the connected Pico. The older firmware
returns 404 for `wake`; it needs serial maintenance to receive the update.

Input requests are never automatically retried. A failed request can have sent
some input already. The server rejects the last 32 command IDs until restart;
this is bounded replay protection, not durable delivery tracking. Inspect the
screen and use `release` before deciding whether to repeat an operation.

## Webcam

The webcam is accessible as `/dev/video0`. Its initial frames may be white:

```sh
python3 tools/webcam.py --fps 5 --warmup 60
```

This keeps capturing for a minute and leaves the latest frame at
`.thonny/webcam.jpg`; Codex can inspect that file. `shell.nix` includes ffmpeg.
The camera capture rate defaults to 5 FPS; `--fps` sets the input rate before
opening the device. The saved image updates once per second independently.
This camera supports 5, 10, 15, 20, 25, and 30 FPS in MJPEG mode at both
640×480 and 1280×720. The default is the verified 640×480 at 5 FPS;
use `--size 1280x720` for a higher-resolution capture.
Lowering the actual camera input rate to 5 FPS recovered the image.

## Preservation, maintenance, and recovery

The original installed scripts are preserved byte for byte as `/normal_boot.py`
and `/normal_main.py`. The standalone branch executes them in order. It keeps
the existing WOL service on port **8081**, webhook behavior, and credentials.
USB control source is in `projects/usb_control/`. Wake-on-LAN and the TCP proxy
are separate projects alongside it. Installed app versions can differ from
repository sources; inspect and back up the board before deploying any project.
Thonny instructions are in [thonny.md](thonny.md).

The existing `/.pico-development` watchdog marker is still present. Consequently
the preserved app's watchdog remains disabled as in the previous setup. To
restore its watchdog, connect through Thonny and run `tools/pico.py development
off`, then power-cycle. USB control itself never enables a watchdog.

For serial maintenance, plug the Pico back into this computer and launch
`./thonny-pico`. Thonny interrupts the control service to open the REPL, so the
HTTP service stops during maintenance. Hard-reset or unplug/replug after
closing Thonny to start the application again. USB HID initialization/reset
intentionally re-enumerates the device; this is distinct from watchdog resets.

Deploy updates with `python3 tools/deploy_hid.py` from an idle Thonny REPL. It
backs up non-secret scripts locally, preserves existing `normal_*` files,
uploads and verifies dependencies, then writes the two startup entrypoints last.
Local backups are kept under `.thonny/backups/`.
It requires no firmware replacement or pip installation.

To uninstall from an idle Thonny session, download the preserved files locally
with `tools/pico.py get`, then upload `normal_boot.py` to `/boot.py` and
`normal_main.py` to `/main.py`; close Thonny and power-cycle. Keep local backup
files until you have checked standalone operation.

Validation tools:

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_hid_linux.py  # Pico attached to this Linux computer
```

The Linux check exclusively grabs the Pico's mouse to keep test clicks away
from the desktop. If keyd already owns its keyboard, it tests a bare Shift tap
without typing into the desktop; full printable-key capture then remains for
a host capture test. It also checks duplicate rejection and verifies that an
invalid batch sends no input. Close any other program grabbing the test mouse.

USB keyboard input was confirmed on the target computer. Linux checks also
verified mouse events, authentication, duplicate rejection, and invalid-batch handling.
The standalone branch and return to USB mode were tested; actual wall-charger
detection still needs a physical plug-in test.
