import sys
import serial

# ToDo: Erweiterung verschiedener Farbräume
# ToDo: Entkopplung Matrix und Schnittstelle
#       Aktuell wird ein Schnittstellen-Objekt vom Objekt der Klasse RGBBasis aufgerufen. So ist es z.B. nicht möglich
#       an das gleiche Schnittstellen-Objekt verschiedene Objekte der RGBBasis zu schicken.
# ToDo: Grösse der Matrix frei wählbar, nicht auf 8 x 8 fixiert
# ToDo: Ausgabe png-Datei ergänzen
# ToDo: Datenkapselung mit get und set umsetzen


class RGBBasis:
    """
    Basisklasse RGB-Matrix
    """
    def __init__(self, port='', default_color=(0, 0, 0)):
        """
        RGBBasis Objekt Konstruktor
        :param port: string, COM-Port -> siehe Geräte-Manager
        :param default_color: list, [R, G, B] -> [0..255, 0..255, 0..255]
        https://de.wikipedia.org/wiki/RGB-Farbraum

        Attribut: "rgb_matrix[zeile][spalte]" wird mit default_color initialisiert (zeile = 0..7, spalte = 0..7)
        """
        self.port = port
        self.default_color = default_color
        self.interface = UART2FPGA(enable=True, port=self.port)  # Windows 'COM.. => siehe Geräte Manager'
        self.rgb_matrix = self.init_rgb_matrix()
        self.rgb_bytestream = self.init_rgb_bytestream()

    def init_rgb_matrix(self):
        """
        Initialisierung der 8 x 8 x 3 Matrix für die vereinfachte Farbzuweisung.
        Dimension 8 x 8 ist fix definiert!
        """
        rgb_matrix = []
        for i in range(0, 8, 1):
            led = []
            for j in range(0, 8, 1):
                rgb = self.default_color
                led.extend([rgb])
            rgb_matrix.extend([led])
        return rgb_matrix

    @staticmethod
    def init_rgb_bytestream():
        """
        Initialisierung des 8 x 8 x 3 Bytestreams (Snake-Line), welcher für die Übertragung an die RGB-Matrix (HW)
        Dimension 8 x 8 ist fix definiert!
        https://www.led-genial.de/DIGI-DOT-Panel-8x8-HD-mit-64-x-Digital-LEDs
        """
        rgb_bytestream = []
        for i in range(0, (8 * 8 * 3), 1):
            rgb_bytestream.extend([0])
        return rgb_bytestream

    def rgb_matrix_to_rgb_bytestream(self):
        """
        Transformation der Matrix-Darstellung in die entsprechende Bytestream-Darstellung (Datenstrom).
        """
        for i in range(0, 8, 1):
            for j in range(0, 8, 1):
                if (i % 2) == 0:
                    self.rgb_bytestream[(i * 8 * 3) + (j * 3) + 0] = self.rgb_matrix[i][j][1]  # ROT
                    self.rgb_bytestream[(i * 8 * 3) + (j * 3) + 1] = self.rgb_matrix[i][j][0]  # GRUEN
                    self.rgb_bytestream[(i * 8 * 3) + (j * 3) + 2] = self.rgb_matrix[i][j][2]  # BLAU
                else:
                    self.rgb_bytestream[(i * 8 * 3) + (j * 3) + 0] = ((self.rgb_matrix[i])[::-1])[j][1]  # ROT
                    self.rgb_bytestream[(i * 8 * 3) + (j * 3) + 1] = ((self.rgb_matrix[i])[::-1])[j][0]  # GRUEN
                    self.rgb_bytestream[(i * 8 * 3) + (j * 3) + 2] = ((self.rgb_matrix[i])[::-1])[j][2]  # BLAU

    def open_interface(self):
        """
        Öffnen der entsprechenden Schnittstelle, z.B. UART
        """
        self.interface.open()

    def close_interface(self):
        """
        Schliessen der entsprechenden Schnittstelle, z.B. UART
        """
        self.interface.close()

    def write2rgb(self):
        """
        Entsprechende Matrix auf der RGB-Matrix darstellen.
        1. Transformation
        2. Werte auf Schnittstelle schreiben
        """
        self.rgb_matrix_to_rgb_bytestream()
        self.interface.write(self.rgb_bytestream)

    def __str__(self):
        """
        Klartextausgabe der Klasseneigenschaften
        """
        return 'RGBBasis(Port={}'.format(self.port) + ', default_color={:}'.format(self.default_color) + ')'

    def __repr__(self):
        return 'RGBBasis(port=\'{}\''.format(self.port) + ', default_color={:}'.format(self.default_color) + ')'


class UART2FPGA:
    """
    Klasse für die Beschreibung der Schnittstelle mittels UART
    https://de.wikipedia.org/wiki/Universal_Asynchronous_Receiver_Transmitter
    """
    def __init__(self, enable=True, port='COM43'):
        """
        UART2FPGA Objekt Konstruktor
        :param enable: boolean, Schnittstelle aktivieren?
        :param port: string, COM-Port -> siehe Geräte-Manager
        """
        self.enable = enable
        self.port = port
        self.instanz = None

    def open(self):
        """
        Oeffne UART mit der COM - Bezeichnung
        """
        if self.enable:
            try:
                self.instanz = serial.Serial(self.port, 921600, timeout=0, parity=serial.PARITY_NONE)
            except Exception as e:
                print('uart_open', e)
                sys.exit()
        else:
            print('UART_ENABLE == False')

    def write(self, bytestream):
        """
        Schreiben auf den UART Kanal
        """
        if self.enable:
            try:
                if len(bytestream) == 8 * 8 * 3:
                    for i in range(0, 8, 1):
                        uart_string = '<{:02x}'.format(i + 1)  # https://pyformat.info/
                        for j in range(0, 8, 1):
                            uart_string += '{:02X}'.format(bytestream[(i * 8 * 3) + (j * 3) + 0])
                            uart_string += '{:02X}'.format(bytestream[(i * 8 * 3) + (j * 3) + 1])
                            uart_string += '{:02X}'.format(bytestream[(i * 8 * 3) + (j * 3) + 2])
                        uart_string += '>'
                        self.instanz.write(uart_string.encode())  # write a string
            except Exception as e:
                print('uart_write', e)
                sys.exit()

    def close(self):
        """
        Schliessen des UART Kanals.
        """
        if self.enable:
            try:
                self.instanz.close()
            except Exception as e:
                print('uart_close', e)
                sys.exit()

    def __str__(self):
        """
        Klartextausgabe der Klasseneigenschaften
        """
        return 'UART2FPGA(enable={}'.format(self.enable) + ', port={}'.format(self.port) + ')'

    def __repr__(self):
        return 'UART2FPGA(enable={}'.format(self.enable) + ', port=\'{}\''.format(self.port) + ')'


if __name__ == '__main__':
    print('_START_AUFGABE_1.py => __main__')
    rgb = RGBBasis(port='COM6', default_color=[0, 2, 3])
    print(rgb)
    rgb.rgb_matrix[0][0] = [1, 0, 0]
    rgb.open_interface()
    rgb.write2rgb()
    rgb.close_interface()
