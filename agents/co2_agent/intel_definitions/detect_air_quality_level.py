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
        "status": "success",
        "air_quality": quality
    }


INTELLIGENCE_INFO = {

    "intelligence_name":
        "Air Quality Classification Intelligence",

    "description":
        "Classifies air quality based on CO2 concentration",

    "category":
        "environment",

    "function_name":
        "detect_air_quality_level",

    "sample_data":
        850
}