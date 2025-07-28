from datetime import datetime

def calculate_average_noise(values):
    return round(sum(values) / len(values), 2) if values else 0

def get_current_timestamp():
    return datetime.utcnow().isoformat()

def calculate_min_noise(values):
    return min(values) if values else None

def calculate_max_noise(values):
    return max(values) if values else None

def get_data_point_count(values):
    return len(values)

def get_unit():
    return "dB"  # decibels for noise
