import numpy as np
from collections import deque

# Store the last 10 exposure checks (rolling window)
HISTORY_LENGTH = 10
exposure_history = deque(maxlen=HISTORY_LENGTH)

def detect_anomaly(current_exposure, max_history=HISTORY_LENGTH):
    """
    Detects if the current exposure is a statistical outlier.
    Returns: (is_anomaly, percentage_deviation)
    """
    exposure_history.append(current_exposure)
    
    # Need at least 5 data points to detect an anomaly
    if len(exposure_history) < 5:
        return False, 0.0
    
    # Calculate mean and standard deviation
    mean = np.mean(list(exposure_history)[:-1])  # Exclude current
    std = np.std(list(exposure_history)[:-1])
    
    # If std is zero, no variance detected
    if std == 0:
        return False, 0.0
    
    # Calculate Z-score (how many standard deviations away is the current value)
    z_score = abs(current_exposure - mean) / std
    
    # If Z-score > 2.5, it's a statistical anomaly (99% confidence)
    if z_score > 2.5:
        deviation_percent = ((current_exposure - mean) / mean) * 100
        return True, round(deviation_percent, 2)
    
    return False, 0.0
