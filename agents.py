from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing import Literal
from state import AgentState
from tools import fetch_risk_data, query_policy, send_slack_alert

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
        "You are a supervisor managing workers: Data_Agent, RAG_Agent, Alert_Agent.\n"
        "Data_Agent fetches crypto asset prices from CoinGecko.\n"
        "RAG_Agent queries the risk management policy.\n"
        "Alert_Agent sends a Slack message.\n"
        "Given the conversation, determine who should act next.\n"
        "If the user's request has been fully satisfied, or if all necessary alerts have been sent, respond with FINISH."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nWho should act next? Select one of: {options}"),
        MessagesPlaceholder(variable_name="messages")
    ]).partial(options=str(options))
    
    chain = prompt | llm.with_structured_output(Route)
    response = chain.invoke({"messages": state["messages"]})
    
    return {"next": response.next}

# --- Worker Agents ---

def create_worker_node(tools, name, system_prompt):
    llm = ChatAnthropic(model="kr/claude-sonnet-4")
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    
    def worker_node(state: AgentState):
        result = agent.invoke({"messages": state["messages"]})
        last_message = result["messages"][-1]
        return {"messages": [HumanMessage(content=f"[{name}] {last_message.content}", name=name)]}
        
    return worker_node

data_agent_node = create_worker_node(
    [fetch_risk_data], 
    "Data_Agent", 
    "You are a data retrieval agent. Your job is to use the fetch_risk_data tool to get live portfolio balances and positions from the user's Binance Testnet account and report them back. Make sure to explicitly mention the portfolio name, total exposure, and margin usage so the Alert_Agent can use them."
)

rag_agent_node = create_worker_node(
    [query_policy], 
    "RAG_Agent", 
    "You are a policy checking agent. Use the query_policy tool to find relevant risk policies and report them back."
)

alert_agent_node = create_worker_node(
    [send_slack_alert], 
    "Alert_Agent", 
    "You are an alerting agent. Your job is to read the conversation, extract the necessary metrics (portfolio name, current margin as a decimal, policy threshold as a decimal, total exposure as a float, and a dictionary of individual asset balances), and use the send_slack_alert tool to notify the team about high risk portfolios."
)
