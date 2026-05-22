def classify_traffic_level(traffic_value):

    if traffic_value < 30:

        level = "Light"

    elif traffic_value < 60:

        level = "Moderate"

    elif traffic_value < 80:

        level = "Busy"

    else:

        level = "Congested"

    return {
        "traffic_level": level
    }