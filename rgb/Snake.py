import time

from rgb import LOCAL_RGB_MATRIX as rgb

OBEN = 0
RECHTS = 1
UNTEN = 2
LINKS = 3

richtungen = [None] * 4
richtungen[OBEN] = (0, -1)
richtungen[RECHTS] = (1, 0)
richtungen[UNTEN] = (0, 1)
richtungen[LINKS] = (-1, 0)

wurm = [50, 250, 50]
start = (3, 3)
richtung = RECHTS

led_array = rgb.RGBBasis()
led_array.open_interface()
time.sleep(0.1)
led_array.write2rgb()

benutzt = []
for _ in range(8):
    benutzt.append([False] * 8)

x, y = start
dx, dy = richtungen[richtung]

while True:
    benutzt[y][x] = True
    led_array.rgb_matrix[y][x] = wurm
    led_array.write2rgb()

    bewegt = False
    for versuch in range(2):
        nx = x + dx
        ny = y + dy

        if (0 <= nx < 8) and (0 <= ny < 8) and not benutzt[ny][nx]:
            bewegt = True
            x, y = nx, ny
            break
        else:
            richtung = (richtung + 1) % len(richtungen)
            dx, dy = richtungen[richtung]

    if not bewegt:
        break

    time.sleep(0.1)

led_array.close_interface()

