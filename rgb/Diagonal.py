import time
from copy import deepcopy
from rgb import LOCAL_RGB_MATRIX as rgb

farbe = [200, 0, 0]

led_array = rgb.RGBBasis()
led_array.open_interface()

matrix = led_array.rgb_matrix

matrix[0][0] = farbe
led_array.write2rgb()

for _ in range(16):
    time.sleep(0.3)

    # Obere Zeile in untere kopieren
    for zeile in range(7, 0, -1):
        matrix[zeile] = deepcopy(matrix[zeile-1])

    # Die erste Zeile um ein nach rechts schieben
    for spalte in range(7, 0, -1):
        matrix[0][spalte] = matrix[0][spalte-1]

    # Und oben links Zelle "auslöschen"
    matrix[0][0] = [0, 0, 0]

    led_array.write2rgb()

led_array.close_interface()

