def classify_humidity_level(humidity_value):

    if humidity_value < 30:

        level = "Dry"

    elif humidity_value < 60:

        level = "Comfortable"

    else:

        level = "Humid"

    return {
        "humidity_level": level
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Humidity Level Classification",

    "description": "Classifies humidity conditions",

    "category": "environment",

    "function_name": "classify_humidity_level",

    "sample_data": 75
}