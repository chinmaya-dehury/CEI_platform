def detect_traffic_congestion(traffic_value):

    THRESHOLD = 80

    if traffic_value > THRESHOLD:

        return {
            "status": "alert",
            "message": "Heavy traffic congestion detected"
        }

    return {
        "status": "normal"
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Traffic Congestion Intelligence",

    "description": "Detects heavy traffic congestion",

    "category": "transport",

    "function_name": "detect_traffic_congestion",

    "sample_data": 90
}