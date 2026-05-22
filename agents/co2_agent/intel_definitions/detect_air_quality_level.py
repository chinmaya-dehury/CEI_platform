def detect_air_quality_level(co2_value):

    if co2_value < 400:

        quality = "Excellent"

    elif co2_value < 800:

        quality = "Moderate"

    elif co2_value < 1200:

        quality = "Poor"

    else:

        quality = "Hazardous"

    return {
        "air_quality": quality
    }