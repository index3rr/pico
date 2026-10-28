# USB must be configured before main.py. Wi-Fi is configured by the selected app.
try:
    import pico_usb
    pico_usb.setup()
except Exception as exc:
    print('Pico USB setup failed:', exc)
