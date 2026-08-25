import os
import requests
from dotenv import load_dotenv
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Get free key from newsapi.org

def get_market_sentiment():
    if not NEWS_API_KEY:
        return {"sentiment": "NEUTRAL", "headlines": []}  # Skip if no key
    
    url = f"https://newsapi.org/v2/everything?q=crypto&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize=5"
    try:
        res = requests.get(url, timeout=5).json()
        articles = res.get('articles', [])
        headline_list = [a['title'] for a in articles]
        headlines = " ".join(headline_list).lower()
        
        bad_words = ['sec', 'hack', 'crash', 'liquidate', 'war', 'ban', 'fraud']
        bad_count = sum(1 for word in bad_words if word in headlines)
        
        if bad_count >= 2:
            return {"sentiment": "BEARISH", "headlines": headline_list}
        return {"sentiment": "NEUTRAL", "headlines": headline_list}
    except:
        return {"sentiment": "NEUTRAL", "headlines": []}
