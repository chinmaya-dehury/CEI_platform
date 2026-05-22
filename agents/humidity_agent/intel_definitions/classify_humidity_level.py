def classify_humidity_level(humidity_value):

    if humidity_value < 30:

        level = "Dry"

    elif humidity_value < 60:

        level = "Comfortable"

    elif humidity_value < 80:

        level = "Humid"

    else:

        level = "Very Humid"

    return {
        "status": "success",
        "humidity_level": level
    }