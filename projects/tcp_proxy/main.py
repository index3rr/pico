import asyncio
from machine import Pin
import time
import webhook

# --- Config ---
LISTEN_PORT = 9011
FORWARD_HOST = "91.218.209.33"
FORWARD_PORT = 9001

led = Pin("LED", Pin.OUT)
active_connections = 0

def fmt_bytes(n):
    if n < 1024: return f"{n}B"
    if n < 1024**2: return f"{n//1024}KB"
    return f"{n//1024//1024}MB"


async def pipe(reader, writer, stats, key):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            stats[key] += len(data)
            writer.write(data)
            await writer.drain()
    except:
        pass
    finally:
        writer.close()

async def handle_client(reader, writer):
    global active_connections
    active_connections += 1

    peer = writer.get_extra_info("peername")
    peer_str = f"{peer[0]}:{peer[1]}" if peer else "unknown"
    print(f"+ Connection from {peer_str} (total: {active_connections})")
    webhook.send(f"**Connection opened** from {peer_str} - active: {active_connections}")
    
    stats = {"tx": 0, "rx": 0}

    try:
        up_reader, up_writer = await asyncio.open_connection(FORWARD_HOST, FORWARD_PORT)
        await asyncio.gather(
            pipe(reader, up_writer, stats, "tx"),
            pipe(up_reader, writer, stats, "rx"),
        )
    except Exception as e:
        print("Error:", e)
        webhook.send(f"️**Connection error** from {peer_str}: {e}")
    finally:
        active_connections -= 1
        writer.close()
        tx, rx = fmt_bytes(stats["tx"]), fmt_bytes(stats["rx"])
        print(f"Connection closed {peer_str} | sent {tx} recv {rx} (total: {active_connections})")
        webhook.send(f"**Connection closed** {peer_str} | up {tx} down {rx} - active: {active_connections}")

async def blink():
    while True:
        if active_connections > 0:
            led.on()
            await asyncio.sleep(0.1)
        else:
            led.on()
            await asyncio.sleep(0.1)
            led.off()
            await asyncio.sleep(0.9)

async def main():
    import network
    wlan = network.WLAN(network.STA_IF)
    while not wlan.isconnected():
        await asyncio.sleep(0.5)

    server = await asyncio.start_server(handle_client, "0.0.0.0", LISTEN_PORT)
    print("Ready")

    while True:
        await asyncio.sleep(3600)

async def start():
    await asyncio.gather(main(), blink())

asyncio.run(start())
