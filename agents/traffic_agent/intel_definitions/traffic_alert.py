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