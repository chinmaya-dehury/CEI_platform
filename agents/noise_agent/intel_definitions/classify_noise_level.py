def classify_noise_level(noise_value):

    if noise_value < 40:

        level = "Quiet"

    elif noise_value < 70:

        level = "Moderate"

    elif noise_value < 90:

        level = "Loud"

    else:

        level = "Hazardous"

    return {
        "noise_level": level
    }