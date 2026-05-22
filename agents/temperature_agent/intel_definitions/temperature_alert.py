def detect_abnormal_temperature(temperature_value):

    THRESHOLD = 40

    if temperature_value > THRESHOLD:

        return {
            "status": "alert",
            "message": "Abnormal temperature detected"
        }

    return {
        "status": "normal"
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Temperature Alert Intelligence",

    "description": "Detects abnormal temperature increase",

    "category": "environment",

    "function_name": "detect_abnormal_temperature",

    "sample_data": 45
}