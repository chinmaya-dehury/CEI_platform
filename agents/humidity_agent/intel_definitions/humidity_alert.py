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
