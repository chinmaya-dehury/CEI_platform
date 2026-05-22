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