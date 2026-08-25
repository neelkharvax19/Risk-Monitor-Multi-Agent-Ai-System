import json
import os
from datetime import datetime

def save_audit_log(risk_metrics, policy_context, action_taken, policy_details="No additional details provided."):
    os.makedirs("audit_reports", exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "metrics": risk_metrics,
        "policy_triggered": policy_context,
        "policy_details": policy_details,
        "action": action_taken
    }
    filename = f"audit_reports/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Audit log saved: {filename}")
