import network
import socket
import time
import webhook
from machine import Pin
from secrets import WAKE_KEY

TARGET_MAC = bytes([0xAC, 0x22, 0x0B, 0x4B, 0x98, 0x5F])
TARGET_IP = "192.168.0.95"
TARGET_PORT = 22
BROADCAST_IP = "255.255.255.255"
WOL_PORT = 9
HTTP_PORT = 80
POLL_TIMEOUT = 90

led = Pin("LED", Pin.OUT)

def build_magic_packet(mac):
    return b'\xff' * 6 + mac * 16

def send_wol():
    mac_hex = ':'.join(f'{b:02x}' for b in TARGET_MAC)
    webhook.send(f"Sending WOL to {mac_hex}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(build_magic_packet(TARGET_MAC), (BROADCAST_IP, WOL_PORT))
    sock.close()
    webhook.send("WOL sent")

def port_open(host, port, timeout=3):
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False
    finally:
        if s:
            try:
                s.close()
            except:
                pass

def serve_forever():
    wlan = network.WLAN(network.STA_IF)
    while not wlan.isconnected():
        time.sleep(0.5)

    addr = socket.getaddrinfo("0.0.0.0", HTTP_PORT)[0][-1]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(1)

    ip = wlan.ifconfig()[0]
    webhook.send(f"WOL server ready on {ip}:{HTTP_PORT}")

    while True:
        client, addr = server.accept()
        try:
            request = client.recv(1024).decode()
            method, path, _ = request.split(' ', 2)

            if method == "GET" and path.startswith("/wake"):
                key = ""
                if "?" in path:
                    query = path.split("?", 1)[1]
                    for p in query.split("&"):
                        if "=" in p:
                            k, v = p.split("=", 1)
                            if k == "key":
                                key = v

                if key == WAKE_KEY:
                    send_wol()
                    webhook.send(f"Waiting for {TARGET_IP}:{TARGET_PORT} to open...")

                    start = time.ticks_ms()
                    ok = False
                    while time.ticks_diff(time.ticks_ms(), start) < POLL_TIMEOUT * 1000:
                        if port_open(TARGET_IP, TARGET_PORT):
                            ok = True
                            break
                        led.on()
                        time.sleep(0.05)
                        led.off()
                        time.sleep(0.95)

                    if ok:
                        led.on()
                        time.sleep(0.5)
                        led.off()
                        client.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nWOL sent")
                        webhook.send(f"{TARGET_IP}:{TARGET_PORT} is online")
                    else:
                        client.sendall(b"HTTP/1.0 504 Gateway Timeout\r\nContent-Type: text/plain\r\n\r\nTimed out")
                        webhook.send(f"Timeout waiting for {TARGET_IP}:{TARGET_PORT}")
                else:
                    client.sendall(b"HTTP/1.0 401 Unauthorized\r\nContent-Type: text/plain\r\n\r\nBad key")
                    webhook.send(f"Bad wake key attempt: {key}")
            else:
                client.sendall(b"HTTP/1.0 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot found")
        except Exception as e:
            webhook.send("Client error: " + str(e))
        finally:
            client.close()

serve_forever()
