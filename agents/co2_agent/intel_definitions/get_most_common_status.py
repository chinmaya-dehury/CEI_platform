from collections import Counter

def get_most_common_status(statuses):
    return Counter(statuses).most_common(1)[0][0] if statuses else None
