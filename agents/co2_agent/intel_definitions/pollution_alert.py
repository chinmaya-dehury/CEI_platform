def detect_abnormal_co2(co2_value):

    THRESHOLD = 800

    if co2_value > THRESHOLD:

        return {
            "status": "alert",
            "message": "Abnormal CO2 increase detected"
        }

    return {
        "status": "normal"
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Pollution Alert Intelligence",

    "description": "Detects abnormal CO2 increase",

    "category": "environment",

    "function_name": "detect_abnormal_co2",

    "sample_data": 850
}