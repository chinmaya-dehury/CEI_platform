def analyze_humidity_trend(humidity_data):

    if len(humidity_data) < 2:

        return {
            "status": "insufficient data"
        }

    if humidity_data[-1] > humidity_data[0]:

        trend = "Increasing"

    elif humidity_data[-1] < humidity_data[0]:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {
        "trend": trend
    }