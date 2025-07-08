from datetime import datetime
from collections import Counter

def calculate_average_temperature(values):
    return round(sum(values) / len(values), 2) if values else 0

def get_current_timestamp():
    return datetime.utcnow().isoformat()

def calculate_min_temperature(values):
    return min(values) if values else None

def calculate_max_temperature(values):
    return max(values) if values else None

def get_data_point_count(values):
    return len(values)

def get_unit():
    return "°C"  # or "Celsius" based on your metadata

def get_status_distribution(statuses):
    return dict(Counter(statuses)) if statuses else {}
