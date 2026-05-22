def detect_abnormal_humidity(humidity_value):

    THRESHOLD = 80

    if humidity_value > THRESHOLD:

        return {
            "status": "alert",
            "message": "Abnormal humidity detected"
        }

    return {
        "status": "normal"
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Humidity Alert Intelligence",

    "description": "Detects abnormal humidity increase",

    "category": "environment",

    "function_name": "detect_abnormal_humidity",

    "sample_data": 85
}