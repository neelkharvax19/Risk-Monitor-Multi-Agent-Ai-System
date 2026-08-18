import json
import os
import requests
from langchain_core.tools import tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings
import hashlib
import hmac
import time
import ccxt
from slack_sender import send_rich_risk_alert as core_send_rich_alert

# Initialize global embeddings and index instances
_embeddings = None
_index = None

def get_pinecone_setup():
    global _embeddings, _index
    if _index is not None:
        return _embeddings, _index
    
    # Initialize embeddings
    _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Initialize Pinecone
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("PINECONE_API_KEY not set properly in .env")

    pc = Pinecone(api_key=api_key)
    index_name = "risk-policies-index"
    
    try:
        _index = pc.Index(index_name)
    except Exception as e:
        raise ConnectionError(f"Could not connect to Pinecone index: {e}")
        
    return _embeddings, _index

@tool
def fetch_risk_data(query: str = "balance") -> str:
    """
    Fetches the live account balances and positions from the Binance Demo environment.
    """
    api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
    secret_key = os.environ.get("BINANCE_TESTNET_SECRET")
    base_url = "https://demo-api.binance.com/api"
    
    if not api_key or not secret_key:
        return "Error: BINANCE_TESTNET_API_KEY or BINANCE_TESTNET_SECRET not found in .env file."
        
    try:
        endpoint = "/v3/account"
        
        # Sync time with Binance server to avoid signature failures due to local clock skew
        time_resp = requests.get(f"{base_url}/v3/time", timeout=5)
        time_resp.raise_for_status()
        timestamp = time_resp.json()['serverTime']
        
        # Build query string
        query_string = f"timestamp={timestamp}"
        
        # Generate HMAC SHA256 signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Build full URL
        url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
        
        headers = {
            "X-MBX-APIKEY": api_key
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # We only want to return balances that are > 0 to save context space
        non_zero_balances = {}
        total_exposure = 0.0
        if 'balances' in data:
            for item in data['balances']:
                total = float(item['free']) + float(item['locked'])
                if total > 0:
                    non_zero_balances[item['asset']] = total
                    if item['asset'] in ['USDT', 'USDC']:
                        total_exposure += total
                    
        return json.dumps({
            "portfolio": "My_Demo_Account",
            "live_balances": non_zero_balances,
            "exposure": total_exposure,
            "margin": 0.10  # Assumed 10% margin usage for demo
        })
    except Exception as e:
        return f"Error fetching account data from Binance Demo: {e}"

@tool
def query_policy(query: str) -> str:
    """
    Queries the risk management policy database for rules and thresholds.
    Use this to look up policies on margin limits, exposure limits, and alert requirements.
    """
    embedder, index = get_pinecone_setup()
    
    try:
        # Generate embedding for the query
        query_embedding = embedder.embed_query(query)
        
        # Query Pinecone directly
        results = index.query(vector=query_embedding, top_k=2, include_metadata=True)
        
        # Extract text from matches
        if not results.get('matches'):
            return "No relevant policy found."
            
        texts = []
        for match in results['matches']:
            if 'metadata' in match and 'text' in match['metadata']:
                texts.append(match['metadata']['text'])
            else:
                texts.append(f"Match ID: {match['id']} (No text metadata found)")
        
        return "\n\n".join(texts)
    except Exception as e:
        return f"Error querying vector store: {e}"

@tool
def send_slack_alert(portfolio_name: str, margin: float, threshold: float, exposure: float, balances: dict = None) -> str:
    """
    Sends a rich, formatted risk breach alert to the #risk-alerts Slack channel.
    Use this when a portfolio breaches policy limits.
    """
    try:
        result = core_send_rich_alert(
            channel="#risk-alerts",
            portfolio_name=portfolio_name,
            margin=margin,
            threshold=threshold,
            exposure=exposure,
            balances=balances
        )
        if result:
            return "Success: Rich alert sent to Slack."
        else:
            return "Failed to send Slack alert."
    except Exception as e:
        return f"Error sending rich slack alert: {e}"
