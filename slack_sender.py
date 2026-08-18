import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

# Initialize the Slack client
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if not SLACK_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN not found in .env file. Please add it.")

client = WebClient(token=SLACK_TOKEN)

def send_slack_alert(channel: str, message: str, thread_ts: str = None) -> dict:
    """
    Send an alert to a Slack channel.

    Parameters:
    - channel: Slack channel ID or name (e.g., '#risk-alerts' or 'C1234567890')
    - message: The text to send
    - thread_ts: Optional thread timestamp to reply in a thread

    Returns:
    - The Slack API response
    """
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message,
            thread_ts=thread_ts,
            mrkdwn=True  # Enables bold, italics, etc.
        )
        print(f"[SUCCESS] Alert sent to Slack channel: {channel}")
        return response.data
    except SlackApiError as e:
        print(f"[ERROR] Slack API error: {e.response['error']}")
        return None

def send_rich_risk_alert(channel: str, portfolio_name: str, margin: float, threshold: float, exposure: float, balances: dict = None) -> dict:
    """
    Send a formatted risk breach alert with rich formatting.
    """
    
    balances_text = ""
    if balances:
        balances_text = "*Asset Breakdown:*\n"
        for asset, amount in balances.items():
            balances_text += f"• {asset}: *{float(amount):,.2f}*\n"

    # Build a formatted message using Slack's mrkdwn
    message = f"""*🚨 URGENT RISK ALERT - Portfolio {portfolio_name}* 🚨

*POLICY BREACH DETECTED*
• Portfolio: *{portfolio_name}*
• Current Margin: *{margin*100:.1f}%* (BREACH)
• Policy Threshold: *{threshold*100:.1f}%*
• Breach Amount: *{(margin - threshold)*100:.1f}%* over limit

*Risk Details:*
• Total Exposure: *${exposure:,.2f}*
{balances_text}• Risk Classification: *HIGH RISK*

*IMMEDIATE ACTION REQUIRED*
Risk management review needed for portfolio rebalancing.

@channel @risk-team
"""
    return send_slack_alert(channel, message)
