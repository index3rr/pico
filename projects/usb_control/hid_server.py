"""Small authenticated LAN service for explicit HID commands; no remote eval."""
import gc
import json
import network
import socket
import time

import pico_usb
from hid_protocol import read_request, validate
from usb.device.keyboard import KeyCode


def check(sent):
    if not sent:
        raise OSError('USB host unavailable or not polling input')


def release():
    if pico_usb.ready():
        check(pico_usb.keyboard.send_keys((), timeout_ms=250))
        check(pico_usb.mouse.report())


def perform(prepared):
    if not pico_usb.ready():
        raise OSError('USB keyboard/mouse is not configured by the host')
    try:
        for action in prepared:
            if action[0] == 'keys':
                for keys in action[1]:
                    check(pico_usb.keyboard.send_keys(keys, timeout_ms=250))
                    time.sleep_ms(20)
                    check(pico_usb.keyboard.send_keys((), timeout_ms=250))
                    time.sleep_ms(20)
            elif action[0] == 'move':
                dx, dy = action[1:]
                while dx or dy:
                    x, y = max(-127, min(127, dx)), max(-127, min(127, dy))
                    check(pico_usb.mouse.report(dx=x, dy=y))
                    dx, dy = dx - x, dy - y
            elif action[0] == 'click':
                check(pico_usb.mouse.report(buttons=action[1]))
                time.sleep_ms(40)
                check(pico_usb.mouse.report())
            elif action[0] == 'scroll':
                check(pico_usb.mouse.report(wheel=action[1]))
            elif action[0] == 'wait':
                time.sleep_ms(action[1])
    finally:
        release()


def response(client, status, data):
    body = json.dumps(data).encode()
    client.sendall(('HTTP/1.1 %s\r\nContent-Type: application/json\r\n'
                    'Content-Length: %d\r\nCache-Control: no-store\r\n'
                    'Connection: close\r\n\r\n' % (status, len(body))).encode())
    client.sendall(body)


def serve():
    from hid_config import TOKEN, PORT
    from secrets import WIFI_SSID, WIFI_PASSWORD
    if not isinstance(TOKEN, str) or len(TOKEN) < 32:
        raise ValueError('Configure a random control token of at least 32 characters')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(hostname='pico')
    last_connect = time.ticks_add(time.ticks_ms(), -20000)
    server = None
    # Cache command IDs before execution. Replays must never emit input again,
    # including after partial failures. The cache lasts until service restart.
    recent = []
    try:
        while True:
            if not wlan.isconnected():
                if server:
                    server.close()
                    server = None
                if time.ticks_diff(time.ticks_ms(), last_connect) >= 15000:
                    try:
                        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
                    except OSError:
                        pass
                    last_connect = time.ticks_ms()
                time.sleep_ms(1000)
                continue
            if server is None:
                server = socket.socket()
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', PORT))
                server.listen(2)
                server.settimeout(1)
                print('Pico HID control: http://%s:%d' % (wlan.ifconfig()[0], PORT))
            try:
                client, address = server.accept()
            except OSError:
                gc.collect()
                continue
            try:
                client.settimeout(3)
                method, path, headers, body = read_request(client)
                if headers.get('authorization') != 'Bearer ' + TOKEN:
                    response(client, '401 Unauthorized', {'ok': False, 'error': 'Unauthorized'})
                elif method == 'GET' and path == '/api/status':
                    response(client, '200 OK', dict(ok=True, mode='usb-control',
                             usb_ready=pico_usb.ready(), ip=wlan.ifconfig()[0]))
                elif method == 'POST' and path == '/api/wake':
                    response(client, '200 OK', dict(ok=True,
                             remote_wakeup_sent=pico_usb.wake()))
                elif method == 'POST' and path == '/api/release':
                    release()
                    response(client, '200 OK', {'ok': True})
                elif method == 'POST' and path == '/api/actions':
                    request = json.loads(body)
                    command_id = request.get('id')
                    if not isinstance(command_id, str) or not 1 <= len(command_id) <= 64:
                        raise ValueError('A command id of 1 to 64 characters is required')
                    if command_id in recent:
                        response(client, '409 Conflict', dict(ok=False, error='Command already seen; not repeated'))
                        continue
                    prepared = validate(request.get('actions'), KeyCode)
                    recent.append(command_id)
                    if len(recent) > 32:
                        recent.pop(0)
                    perform(prepared)
                    response(client, '200 OK', dict(ok=True, id=command_id))
                else:
                    response(client, '404 Not Found', dict(ok=False, error='Unknown endpoint'))
            except (ValueError, TypeError, AttributeError) as exc:
                try:
                    response(client, '400 Bad Request', dict(ok=False, error=str(exc)))
                except OSError:
                    pass
            except OSError as exc:
                try:
                    response(client, '503 Service Unavailable', dict(ok=False, error=str(exc),
                             note='Input may be partially applied; it was not retried'))
                except OSError:
                    pass
            finally:
                client.close()
                gc.collect()
    finally:
        if server:
            server.close()
        release()
