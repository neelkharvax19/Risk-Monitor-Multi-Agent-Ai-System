def should_rebalance(exposure, margin, threshold=0.80):
    # Simulate cost: 0.1% fee + 0.5% slippage
    breach_amount = max(0, margin - threshold)
    potential_loss = exposure * breach_amount * 0.01  # 1% of breach value
    
    # Cost to fix: 0.6% of total exposure
    rebalance_cost = exposure * 0.006  
    
    if potential_loss < rebalance_cost:
        return {"action": "IGNORE", "reason": "Cost > Potential Loss"}
    return {"action": "REBALANCE", "reason": "Risk justifies cost"}
