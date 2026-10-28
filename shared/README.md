# Shared Pico modules

Wake-on-LAN and the TCP proxy use these common files:

- `boot.py`: connect to Wi-Fi and announce the Pico's IP through the webhook.
- `webhook.py`: Discord webhook helper; requires `urequests` on the board.
- `example_secrets.py`: placeholder Wi-Fi, webhook, and wake-key configuration.

Create a private `secrets.py` from the example and fill in the values. Upload
the shared modules to the board's root alongside the selected project's
`main.py`; a `shared/` directory is not required on the board. Never commit or
print actual credentials. USB control also uses the board's Wi-Fi credentials
but provides its own startup files and private generated control token.

For dual-mode operation, the Wi-Fi boot script belongs at `/normal_boot.py`.
Inspect the installed files and retain backups before changing applications.
