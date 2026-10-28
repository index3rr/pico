# Wake-on-LAN

An HTTP service that sends a Wake-on-LAN magic packet and waits for the target
computer's SSH port to become available. Requests use `/wake?key=YOUR_WAKE_KEY`.
Configure the target MAC, IP, and port constants in `main.py` for your network.

For a standalone installation, upload this project's `main.py` and the shared
`boot.py`, `webhook.py`, and private `secrets.py` to the Pico's root. See
[shared setup](../../shared/README.md) and [file transfer](../../docs/thonny.md).
The repository version listens on port 80.

The current dual-mode installation runs its preserved WOL application on wall
power. That installed version listens on port 8081 and differs from this source.
Back up `/normal_boot.py` and `/normal_main.py` before updating it. Updating the
dual-mode standalone app should target those names so the USB startup router
continues to work; do not replace the router with a standalone entrypoint.
