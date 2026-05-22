def analyze_noise_trend(noise_data):

    if len(noise_data) < 2:

        return {
            "status": "insufficient data"
        }

    if noise_data[-1] > noise_data[0]:

        trend = "Increasing"

    elif noise_data[-1] < noise_data[0]:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {
        "status": "success",
        "trend": trend
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Noise Trend Intelligence",

    "description": "Analyzes environmental noise trends",

    "category": "analytics",

    "function_name": "analyze_noise_trend",

    "sample_data": [40, 50, 65, 80]
}