import datetime

def get_time_multiplier():
    now = datetime.datetime.now().hour
    # 2 AM to 7 AM (High risk, low human oversight)
    if 2 <= now < 7:
        return 0.5  # 50% reduction in limits
    return 1.0
