"""Select USB control or the preserved standalone app after each power cycle."""
import sys

try:
    import pico_usb
    control_mode = pico_usb.wait_for_host()
except Exception as exc:
    print('USB detection failed; using standalone app:', exc)
    control_mode = False

if control_mode:
    print('USB host detected: starting keyboard/mouse control')
    try:
        import hid_server
        hid_server.serve()
    except Exception as exc:
        # Stay at the REPL on failure. Never run the standalone app's watchdog
        # while a USB host is attached.
        sys.print_exception(exc)
else:
    print('No USB host: starting preserved standalone app')
    for filename in ('/normal_boot.py', '/normal_main.py'):
        with open(filename) as source:
            exec(compile(source.read(), filename, 'exec'), globals())
