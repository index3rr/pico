import urequests
import json
from secrets import WEBHOOK_URL

def send(msg):
    try:
        payload = json.dumps({"content": msg})
        print("Sending:", payload)
        r = urequests.post(
            WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code, r.text)
        r.close()
    except Exception as e:
        import sys
        sys.print_exception(e)
