# USB control

Wi-Fi-controlled USB keyboard and mouse, with automatic selection of a separate
standalone application when the Pico is powered from a wall charger.

- `boot.py` and `main.py`: initialize USB and select the application.
- `pico_usb.py`: keyboard/mouse interfaces and USB host detection.
- `hid_server.py` and `hid_protocol.py`: authenticated HTTP input service.
- `lib/`: required MicroPython USB libraries and license information.

See [control and deployment](../../docs/control.md) for host commands, webcam
capture, authentication, and installation. The deploy tool preserves the
board's existing standalone app as `/normal_boot.py` and `/normal_main.py`.

