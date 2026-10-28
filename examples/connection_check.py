"""A finite, non-networked check safe to run from Thonny or tools/pico.py."""
import os
import time

print("Connected:", os.uname().machine)
for count in range(5):
    print("Pico connection check", count + 1)
    time.sleep(0.2)
print("Connection check complete")
