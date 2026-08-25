from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing import Literal
from state import AgentState
from tools import fetch_risk_data, query_policy, send_slack_alert
from anomaly_agent import detect_anomaly
import json
import os
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from email_sender import send_email_alert

from agents.macro_agent import get_market_sentiment
from agents.ping_agent import check_exchange_health
from agents.cost_agent import should_rebalance
from agents.timekeeper import get_time_multiplier
from agents.report_agent import save_audit_log

# --- Supervisor Agent ---

members = ["Data_Agent", "RAG_Agent", "Alert_Agent"]
options = ["FINISH"] + members

class Route(BaseModel):
    next: Literal["FINISH", "Data_Agent", "RAG_Agent", "Alert_Agent"]

def supervisor_node(state: AgentState):
    """
    The supervisor node reads the conversation and determines which worker agent should act next.
    """
    llm = ChatAnthropic(model="kr/claude-sonnet-4")
    
    system_prompt = (
        "You are a supervisor managing workers: Data_Agent, RAG_Agent, Alert_Agent, Macro_Agent.\n"
        "Data_Agent fetches crypto asset prices from CoinGecko.\n"
        "RAG_Agent queries the risk management policy.\n"
        "Alert_Agent sends a Slack message.\n"
        "Macro_Agent fetches the latest macro news sentiment and headlines.\n"
        "Given the conversation, determine who should act next.\n"
        "If the user's request has been fully satisfied, or if all necessary alerts have been sent, respond with FINISH."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nWho should act next? Select one of: {options}"),
        MessagesPlaceholder(variable_name="messages")
    ]).partial(options=str(options))
    
    chain = prompt | llm.with_structured_output(Route)
    response = chain.invoke({"messages": state["messages"]})
    next_node = response.next
    
    # Gatekeeper Logic: Run Phase 4 checks if we want to alert
    if next_node == "Alert_Agent" or state.get("alert_triggered"):
        print("---\nNode: Supervisor - Evaluating Context...")

        # 1. Check Exchange Health (Prevents false alerts)
        health = check_exchange_health()
        if health["status"] != "HEALTHY":
            print(f"[Exchange Status] Exchange is {health['status']}. Suppressing alerts until fixed.")
            return {"next": "FINISH", "alert_triggered": False}
        
        sentiment_data = get_market_sentiment()
        sentiment = sentiment_data.get("sentiment", "NEUTRAL")
        headlines = sentiment_data.get("headlines", [])
        dynamic_threshold = 0.60 if sentiment == "BEARISH" else 0.80
        print(f"[Macro Sentiment] Sentiment: {sentiment} | Dynamic Limit: {dynamic_threshold*100}%")
        if headlines:
            print("Latest Crypto Headlines:")
            for h in headlines[:3]:
                print(f"- {h}")

        # 3. Check Time (Sleepy Protocol)
        time_factor = get_time_multiplier()
        final_threshold = dynamic_threshold * time_factor
        print(f"[Time Factor] Time Factor: {time_factor} | Effective Limit: {final_threshold*100}%")

        # Fetch the real policy text from Pinecone for the detailed report
        try:
            active_policy_text = query_policy.invoke("margin utilization limit threshold")
            detailed_policy = f"The AI evaluated the portfolio against this specific rule from the PDF:\n\n\"{active_policy_text.strip()}\"\n\nBecause the portfolio margin is currently safe, no alerts were triggered."
        except Exception as e:
            detailed_policy = "The AI performed a routine check against the active policy. No breaches were found."

        # 4. Cost-Benefit Check (Prevents overtrading)
        metrics = state.get("risk_metrics", {})
        cost_decision = should_rebalance(metrics.get("exposure", 0), metrics.get("margin", 0), threshold=final_threshold)
        if cost_decision["action"] == "IGNORE":
            print(f"[Cost-Benefit] {cost_decision['reason']}. Skipping alert.")
            save_audit_log(metrics, "Routine Margin Check (Safe)", "Suppressed (Cost-Benefit)", detailed_policy)
            return {"next": "FINISH", "alert_triggered": False}

        # 5. Core Breach Logic
        current_margin = metrics.get("margin", 0)
        is_anomaly = state.get("anomaly_detected", False)
        
        if current_margin > final_threshold or is_anomaly:
            if current_margin > final_threshold:
                print(f"[Core Breach] Breach detected! Margin {current_margin} > Threshold {final_threshold}")
            if is_anomaly:
                print(f"[Anomaly] Anomaly confirmed!")
                
            # Save audit proof with detailed breach context
            policy_ctx = "Margin Limit Breach" if current_margin > final_threshold else "Anomaly Detected"
            try:
                breach_details = query_policy.invoke("margin utilization limit threshold")
                breach_explanation = f"BREACH DETECTED! The portfolio violated the following rule from the PDF:\n\n\"{breach_details.strip()}\""
            except:
                breach_explanation = "A policy breach or anomaly was detected requiring immediate attention."
                
            save_audit_log(metrics, policy_ctx, "Slack+Email Alert", breach_explanation)
            
            return {"next": "Alert_Agent"}
        
        print("[All Clear] All clear. Suppressing alert.")
        save_audit_log(metrics, "Routine Margin Check (Safe)", "Suppressed (All Clear)", detailed_policy)
        return {"next": "FINISH", "alert_triggered": False}
        
    return {"next": next_node}

# --- Worker Agents ---

def create_worker_node(tools, name, system_prompt):
    llm = ChatAnthropic(model="kr/claude-sonnet-4")
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    
    def worker_node(state: AgentState):
        result = agent.invoke({"messages": state["messages"]})
        last_message = result["messages"][-1]
        return {"messages": [HumanMessage(content=f"[{name}] {last_message.content}", name=name)]}
        
    return worker_node

_base_data_agent = create_react_agent(ChatAnthropic(model="kr/claude-sonnet-4"), [fetch_risk_data], prompt="You are a data retrieval agent. Your job is to use the fetch_risk_data tool to get live portfolio balances and positions from the user's Binance Testnet account and report them back. Make sure to explicitly mention the portfolio name, total exposure, and margin usage so the Alert_Agent can use them.")

def data_agent_node(state: AgentState):
    result = _base_data_agent.invoke({"messages": state["messages"]})
    last_message = result["messages"][-1]
    
    total_exposure = 0.0
    margin_usage = 0.0
    for msg in result["messages"]:
        if hasattr(msg, 'name') and msg.name == "fetch_risk_data":
            try:
                data = json.loads(msg.content)
                total_exposure = float(data.get("exposure", 0.0))
                margin_usage = float(data.get("margin", 0.0))
            except Exception:
                pass
                
    is_anomaly, dev_pct = detect_anomaly(total_exposure)
    
    updates = {
        "messages": [HumanMessage(content=f"[Data_Agent] {last_message.content}", name="Data_Agent")],
        "anomaly_detected": is_anomaly,
        "anomaly_deviation": dev_pct if is_anomaly else 0.0,
        "risk_metrics": {"portfolio": "My_Demo_Account", "exposure": total_exposure, "margin": margin_usage}
    }
    
    if is_anomaly:
        print(f"🚨 ANOMALY DETECTED! Exposure changed by {dev_pct}% from normal.")
        updates["alert_triggered"] = True
        
    return updates

@tool
def fetch_macro_news(query: str = "") -> str:
    """Fetches the latest macro news sentiment and headlines for the crypto market."""
    data = get_market_sentiment()
    sentiment = data.get("sentiment", "NEUTRAL")
    headlines = data.get("headlines", [])
    result = f"Current Sentiment: {sentiment}\nLatest Headlines:\n"
    for h in headlines:
        result += f"- {h}\n"
    return result

macro_agent_node = create_worker_node(
    [fetch_macro_news],
    "Macro_Agent",
    "You are a macro-economic news agent. Use the fetch_macro_news tool to retrieve the latest crypto news sentiment and headlines, and report them back to the user."
)

rag_agent_node = create_worker_node(
    [query_policy], 
    "RAG_Agent", 
    "You are a policy checking agent. Use the query_policy tool to find relevant risk policies and report them back."
)

_base_alert_agent = create_react_agent(
    ChatAnthropic(model="kr/claude-sonnet-4"), 
    [send_slack_alert], 
    prompt="You are an alerting agent. Your job is to read the conversation, extract the necessary metrics (portfolio name, current margin as a decimal, policy threshold as a decimal, total exposure as a float, and a dictionary of individual asset balances), and use the send_slack_alert tool to notify the team about high risk portfolios."
)

def alert_agent_node(state: AgentState):
    result = _base_alert_agent.invoke({"messages": state["messages"]})
    last_message = result["messages"][-1]
    
    if state.get("anomaly_detected", False):
        metrics = state.get("risk_metrics", {})
        email_body = f"""
        URGENT ANOMALY DETECTED
        Portfolio: {metrics.get('portfolio', 'Unknown')}
        Current Exposure: ${metrics.get('exposure', 0)}
        Deviation: {state.get('anomaly_deviation', 0)}%
        Action: Immediate manual review required.
        """
        send_email_alert(
            subject="[CRITICAL] Risk Anomaly Detected",
            body=email_body,
            recipient=os.getenv("ALERT_EMAIL", "risk-team@yourcompany.com")
        )
        
    return {"messages": [HumanMessage(content=f"[Alert_Agent] {last_message.content}", name="Alert_Agent")]}
