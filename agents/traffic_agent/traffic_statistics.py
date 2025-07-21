from datetime import datetime
from collections import Counter

def calculate_average_vehicle_count(values):
    return round(sum(values) / len(values), 2) if values else 0

def get_current_timestamp():
    return datetime.utcnow().isoformat()

def calculate_min_vehicle_count(values):
    return min(values) if values else None

def calculate_max_vehicle_count(values):
    return max(values) if values else None

def get_most_common_congestion_status(statuses):
    return Counter(statuses).most_common(1)[0][0] if statuses else None

def get_data_point_count(values):
    return len(values)
