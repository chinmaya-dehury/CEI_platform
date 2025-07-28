from datetime import datetime

def calculate_average_humidity(values):
    return round(sum(values) / len(values), 2) if values else 0

def get_current_timestamp():
    return datetime.utcnow().isoformat()

def calculate_min_humidity(values):
    return min(values) if values else None

def calculate_max_humidity(values):
    return max(values) if values else None

def get_data_point_count(values):
    return len(values)

def get_unit():
    return "percent"  # or "%" if your team prefers
