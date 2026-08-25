import requests
import time

def check_exchange_health():
    try:
        start = time.time()
        requests.get("https://api.binance.com/api/v3/ping", timeout=3)
        latency = (time.time() - start) * 1000
        if latency > 2000:  # 2 seconds
            return {"status": "SLOW", "latency": latency}
        return {"status": "HEALTHY", "latency": latency}
    except:
        return {"status": "DOWN", "latency": None}
