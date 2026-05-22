def analyze_traffic_trend(traffic_data):

    if len(traffic_data) < 2:

        return {
            "status": "insufficient data"
        }

    if traffic_data[-1] > traffic_data[0]:

        trend = "Increasing"

    elif traffic_data[-1] < traffic_data[0]:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {
        "trend": trend
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Traffic Trend Intelligence",

    "description": "Analyzes traffic congestion trends",

    "category": "analytics",

    "function_name": "analyze_traffic_trend",

    "sample_data": [20, 35, 50, 70]
}