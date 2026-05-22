def classify_temperature_level(temperature_value):

    if temperature_value < 15:

        level = "Cold"

    elif temperature_value < 30:

        level = "Normal"

    elif temperature_value < 40:

        level = "Hot"

    else:

        level = "Extreme Heat"

    return {
        "temperature_level": level
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Temperature Level Classification",

    "description": "Classifies environmental temperature conditions",

    "category": "environment",

    "function_name": "classify_temperature_level",

    "sample_data": 45
}