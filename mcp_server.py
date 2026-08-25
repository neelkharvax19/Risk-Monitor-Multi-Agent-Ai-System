import os
import hashlib
import hmac
import requests
import time
from fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("RiskMonitor")

@mcp.tool()
def fetch_portfolio_risk(api_key: str, secret_key: str) -> dict:
    """Fetches live balance and risk from Binance Demo."""
    base_url = "https://demo.binance.com/api"
    
    # Get timestamp
    time_resp = requests.get("https://demo.binance.com/api/v3/time")
    timestamp = time_resp.json()['serverTime']
    
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{base_url}/v3/account?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": api_key}
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    total = 0.0
    for asset in data.get("balances", []):
        if asset.get("asset") in ["USDT", "USDC"]:
            total += float(asset.get("free", 0))
    
    return {
        "total_exposure": total,
        "margin_utilization": 0.10,  # Placeholder, calculate dynamically if possible
        "raw_data": data
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")  # or "sse" for HTTP
