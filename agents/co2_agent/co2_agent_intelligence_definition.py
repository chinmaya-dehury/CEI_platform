from collections import Counter
from datetime import datetime

def calculate_average(values):
    return round(sum(values) / len(values), 2) if values else 0

def get_current_timestamp():
    return datetime.utcnow().isoformat()

def calculate_min(values):
    return min(values) if values else None

def calculate_max(values):
    return max(values) if values else None

def get_most_common_status(statuses):
    return Counter(statuses).most_common(1)[0][0] if statuses else None

def get_data_point_count(data):
    return len(data)

def get_unit():
    return "ppm"  # Or load from metadata if needed
