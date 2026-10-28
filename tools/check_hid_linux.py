#!/usr/bin/env python3
"""Verify Pico HID events while exclusively grabbing them away from the desktop.

Run only with the Pico plugged into this Linux computer, not the Chromebook.
Requires read access to the Pico's /dev/input/event* nodes (the input group).
"""
import fcntl
import errno
import os
from pathlib import Path
import select
import struct
import time

import hid

EVIOCGRAB = 0x40044590
EVENT = struct.Struct('llHHi')


def main():
    serial = os.environ.get('PICO_SERIAL', 'e66480454f2daf36')
    fds = []
    exclusive_keyboard = False
    exclusive_mouse = False
    found_keyboard = False
    try:
        for path in Path('/sys/class/input').glob('event*'):
            device = (path / 'device').resolve()
            if not any((parent / 'serial').is_file() and
                       (parent / 'serial').read_text().strip() == serial
                       for parent in device.parents):
                continue
            fd = os.open('/dev/input/' + path.name, os.O_RDONLY | os.O_NONBLOCK)
            is_mouse = int((device / 'capabilities/rel').read_text().strip(), 16) != 0
            if not is_mouse:
                found_keyboard = True
            try:
                fcntl.ioctl(fd, EVIOCGRAB, 1)
            except OSError as exc:
                os.close(fd)
                if exc.errno == errno.EBUSY and not is_mouse:
                    print('Keyboard already grabbed by another input service; testing only a bare SHIFT tap, no desktop text')
                    continue
                raise
            if not is_mouse:
                exclusive_keyboard = True
            else:
                exclusive_mouse = True
            fds.append(fd)
        if not exclusive_mouse or not found_keyboard:
            raise RuntimeError('Pico keyboard and mouse were not found; no test input was sent')
        assert hid.request('/api/status')['usb_ready']
        keys = ([{'type': 'text', 'text': 'aA!'}, {'type': 'key', 'keys': ['SHIFT', 'Z']}]
                if exclusive_keyboard else [{'type': 'key', 'keys': ['SHIFT']}])
        hid.actions(keys + [{'type': 'move', 'dx': 17, 'dy': -9},
                     {'type': 'scroll', 'amount': 1},
                     {'type': 'click', 'button': 'left'}])
        events = []
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            ready, _, _ = select.select(fds, [], [], .1)
            for fd in ready:
                data = os.read(fd, EVENT.size * 256)
                events.extend(EVENT.unpack_from(data, pos)[2:]
                              for pos in range(0, len(data), EVENT.size))
        expected = [(2, 0, 17), (2, 1, -9), (2, 8, 1), (1, 272, 1), (1, 272, 0)]
        if exclusive_keyboard:
            expected += [(1, 30, 1), (1, 30, 0), (1, 42, 1), (1, 42, 0),
                         (1, 2, 1), (1, 2, 0), (1, 44, 1), (1, 44, 0)]
        for event in expected:
            assert event in events, ('Missing input event', event, events)
        if exclusive_keyboard:
            print('PASS: keyboard letters, shift, punctuation, and chord received through Linux input')
        else:
            print('PASS: keyboard SHIFT press/release acknowledged by USB; printable keys not tested on desktop')
        print('PASS: mouse movement, wheel, click, and releases received through Linux input')
        command_id = 'linux-hid-check-' + str(time.time_ns())
        hid.actions([{'type': 'wait', 'ms': 0}], command_id=command_id)
        try:
            hid.actions([{'type': 'wait', 'ms': 0}], command_id=command_id)
        except RuntimeError as exc:
            assert 'already seen' in str(exc), exc
        else:
            raise AssertionError('Replay was not rejected')
        try:
            hid.actions([{'type': 'text', 'text': 'should not type'},
                         {'type': 'text', 'text': 'é'}])
        except RuntimeError as exc:
            assert 'Unsupported character' in str(exc), exc
        else:
            raise AssertionError('Invalid batch was accepted')
        # The accepted no-op releases do not change any key state. The invalid
        # batch must likewise not emit any key or relative motion events.
        for fd in fds:
            try:
                data = os.read(fd, EVENT.size * 256)
            except BlockingIOError:
                continue
            extra = [EVENT.unpack_from(data, pos)[2:] for pos in range(0, len(data), EVENT.size)]
            assert not [event for event in extra if event[0] in (1, 2)], extra
        print('PASS: duplicate command rejected; malformed batch emitted no input')
    finally:
        if fds:
            try:
                hid.request('/api/release', {})
            finally:
                for fd in fds:
                    fcntl.ioctl(fd, EVIOCGRAB, 0)
                    os.close(fd)


if __name__ == '__main__':
    main()
