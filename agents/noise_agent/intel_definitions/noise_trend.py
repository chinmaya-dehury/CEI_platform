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
        "trend": trend
    }