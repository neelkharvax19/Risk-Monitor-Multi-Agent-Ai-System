import os
import time
import logging
import schedule
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from main import build_graph

load_dotenv()

# Set up logging so you can track it 24/7
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("risk_monitor.log"),  # Saves logs to a file
        logging.StreamHandler()                  # Also prints to terminal
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
# Build the LangGraph app
app = build_graph()

def run_risk_check():
    """Executes the full Multi-Agent System"""
    logger.info(" Running scheduled risk check...")
    
    try:
        user_input = (
            "Check the risk for my Binance Testnet account. First get my live account balances, then check the policy for any exposure or margin limit breaches, "
            "and if it breaches the threshold, send an alert."
        )
        
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            # The extra state variables from the prompt are ignored since 
            # they aren't part of our state.py AgentState schema.
        }
        
        # Invoke the exact same LangGraph you already built
        events = app.stream(initial_state, {"recursion_limit": 20})
        
        for s in events:
            for k, v in s.items():
                logger.info(f"Node: {k}")
                if "messages" in v:
                    for m in v["messages"]:
                        safe_content = m.content.encode('ascii', 'replace').decode('ascii')
                        logger.info(f"  {safe_content}")
                if "next" in v:
                    logger.info(f"  Routing to: {v['next']}")
                    
        logger.info(" Risk check complete.")
            
    except Exception as e:
        logger.error(f" Risk check failed with error: {e}")

# --- The Magic: 24/7 Loop ---
if __name__ == "__main__":
    logger.info(" Starting 24/7 Risk Monitor Daemon...")
    logger.info(" System will check risk every 60 seconds.")
    
    # Run once immediately
    run_risk_check()
    
    # Schedule it to run every 60 seconds (1440 times/day = ~15k events/day)
    schedule.every(60).seconds.do(run_risk_check)
    
    # Infinite loop to keep the script alive
    while True:
        schedule.run_pending()
        time.sleep(1)
