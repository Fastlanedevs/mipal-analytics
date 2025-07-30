import random


def generate_profile_color():
    """
    Generates a random, visually pleasing color in hexadecimal format.
    Returns a string in the format '#RRGGBB' with uppercase letters.
    """
    # Use HSV color space for more pleasing colors
    hue = random.randint(0, 360)
    saturation = random.randint(60, 90) / 100
    value = random.randint(75, 100) / 100

    # Convert HSV to RGB
    h = hue / 360
    i = int(h * 6)
    f = h * 6 - i
    p = value * (1 - saturation)
    q = value * (1 - f * saturation)
    t = value * (1 - (1 - f) * saturation)

    if i % 6 == 0:
        r, g, b = value, t, p
    elif i % 6 == 1:
        r, g, b = q, value, p
    elif i % 6 == 2:
        r, g, b = p, value, t
    elif i % 6 == 3:
        r, g, b = p, q, value
    elif i % 6 == 4:
        r, g, b = t, p, value
    else:
        r, g, b = value, p, q

    # Convert to hex format with uppercase letters
    hex_color = f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

    return hex_color
