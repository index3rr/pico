# Pico workflow

- Read `README.md` for the layout and `docs/control.md` for USB control/deployment.
- Start with `python3 tools/hid.py status` for USB keyboard/mouse control. The current
  Pico address is 192.168.0.82:8765; the token is private in `.thonny/hid-token`.
- Do not launch Thonny for network control: entering the REPL stops the service.
  For serial work, reuse an existing bridge (`python3 tools/pico.py status`) or
  launch `./thonny-pico`. Never open a competing serial connection.
- Maintain Wake-on-LAN, TCP proxy, and USB control as peer projects under
  `projects/wake_on_lan/`, `projects/tcp_proxy/`, and `projects/usb_control/`.
  Common modules are in `shared/`.
- The device's root boot.py/main.py currently select USB control or the preserved
  /normal_boot.py and /normal_main.py. Installed app versions may differ from
  repository sources; inspect them before deploying any project.
- Read/back up device files before editing. Never print, commit, or overwrite
  secrets.py. Preserve `.thonny/backups/`, credentials, and Thonny configuration.
- Use `python3 tools/webcam.py --fps 5 --warmup 60` for a fresh camera frame in
  `.thonny/webcam.jpg`; inspect it before choosing coordinates or describing UI.
- Use `python3 tools/webcam.py --fps 5 --warmup 60` for a fresh camera frame;
  inspect it before choosing coordinates or describing the screen. Do not
  capture webcam audio.
- Keep development mode on during REPL work. See `docs/thonny.md` before changing
  the standalone watchdog. Never automatically retry input, execution, or uploads.
- Add dependencies to `shell.nix`, not pip or global installations.
- Run `python3 -m unittest discover -s tests -v` after firmware/protocol changes.
