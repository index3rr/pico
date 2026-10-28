# TCP proxy

An asynchronous TCP forwarding service with connection statistics, LED activity,
and webhook notifications. Configure `LISTEN_PORT`, `FORWARD_HOST`, and
`FORWARD_PORT` in `main.py` for the service you want to forward.

For a standalone installation, upload this project's `main.py` and the shared
`boot.py`, `webhook.py`, and private `secrets.py` to the Pico's root. See
[shared setup](../../shared/README.md) and [file transfer](../../docs/thonny.md).

To use the proxy as the wall-powered app in a dual-mode installation, back up
the existing normal app and deploy the proxy as `/normal_main.py`, with the
shared Wi-Fi boot script as `/normal_boot.py`. Keep the USB control router at
`/boot.py` and `/main.py`.
