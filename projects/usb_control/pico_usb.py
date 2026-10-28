"""USB setup shared by boot.py and the network controller. No input on boot."""
import struct
import time
import machine
import usb.device
from usb.device.hid import HIDInterface
from usb.device.keyboard import KeyboardInterface

keyboard = None
mouse = None
host_seen = False


class Keyboard(KeyboardInterface):
    def on_open(self):
        global host_seen
        super().on_open()
        host_seen = True


class Mouse(HIDInterface):
    # Three buttons, relative X/Y, and vertical wheel. Report protocol only.
    REPORT = bytes.fromhex(
        '05010902a1010901a10005091901290315002501950375018102'
        '95017505810105010930093109381581257f750895038106c0c0'
    )

    def __init__(self):
        super().__init__(self.REPORT, interface_str='Pico Control Mouse')

    def report(self, buttons=0, dx=0, dy=0, wheel=0):
        return self.send_report(struct.pack('Bbbb', buttons, dx, dy, wheel), 250)


def setup():
    global keyboard, mouse
    if keyboard is None:
        keyboard, mouse = Keyboard(), Mouse()
        # Preserve the built-in serial interface for Thonny maintenance.
        usb.device.get().init(keyboard, mouse, builtin_driver=True,
                              remote_wakeup=True)


def wait_for_host(timeout_ms=10000):
    start = time.ticks_ms()
    while not host_seen and time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        time.sleep_ms(20)
    return host_seen


def ready():
    return keyboard is not None and keyboard.is_open() and mouse.is_open()


def wake():
    # This sends a USB resume signal, not a key. The host must have enabled
    # remote wakeup; False can also mean it is already awake.
    return machine.USBDevice().remote_wakeup()
