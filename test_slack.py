from slack_sender import send_slack_alert

# Send a test message
response = send_slack_alert(
    channel="#risk-alerts",
    message="🔔 *Test Alert*: Your risk monitor is alive and connected!"
)

if response:
    print("Slack test passed! Check your channel.")
else:
    print("Slack test failed. Check your token and channel name.")
