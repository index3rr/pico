import network
import webhook
from secrets import WIFI_SSID, WIFI_PASSWORD 
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(hostname="pico")
wlan.connect(WIFI_SSID, WIFI_PASSWORD)
ip = wlan.ifconfig()[0]
print("IP:", ip)
webhook.send(f"**Pico online** - IP: {ip}")
