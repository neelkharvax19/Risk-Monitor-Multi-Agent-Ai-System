from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    The state for the risk monitor graph.
    """
    # The list of messages representing the conversation history
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # The next node to route to
    next: str
    
    anomaly_detected: bool
    anomaly_deviation: float
    alert_triggered: bool
    risk_metrics: dict
