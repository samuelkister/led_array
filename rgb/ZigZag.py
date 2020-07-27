import time
from itertools import cycle

from rgb import LOCAL_RGB_MATRIX as rgb

farbe = [50, 250, 50]

led_array = rgb.RGBBasis()
led_array.open_interface()
time.sleep(0.1)
led_array.write2rgb()
time.sleep(1.0)

# for l, linie in enumerate(led_array.rgb_matrix):
#     zaehler = range(8) if l % 2 else range(7, -1, -1)

for linie, zaehler in zip(led_array.rgb_matrix, cycle([range(7, -1, -1), range(8)])):
    for spalte in zaehler:
        linie[spalte] = farbe
        
        led_array.write2rgb()
        time.sleep(0.1)

led_array.close_interface()

