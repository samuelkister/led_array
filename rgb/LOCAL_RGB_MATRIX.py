# ======================
# imports
# ======================
import datetime
import email
import os
import threading
import time
import urllib
import webbrowser
from copy import deepcopy
from http import HTTPStatus
from http.server import CGIHTTPRequestHandler, _url_collapse_path, ThreadingHTTPServer
from queue import Queue


class RGBBasis:
    """
    Local replacement to RGB-Matrix.
    It will create a HTML server and draw to it
    """

    def __init__(self, port='', default_color=[0, 0, 0], width=8, height=8):
        """
        RGBBasis Objekt Konstruktor
        :param port: string, COM-Port -> siehe Geräte-Manager
        :param default_color: list, [R, G, B] -> [0..255, 0..255, 0..255]
        https://de.wikipedia.org/wiki/RGB-Farbraum

        Attribut: "rgb_matrix[zeile][spalte]" wird mit default_color initialisiert (zeile = 0..7, spalte = 0..7)
        """
        self.width = width
        self.height = height

        self.default_color = deepcopy(default_color)

        self.rgb_matrix = self.get_filled_matrix(self.default_color)

        self.gui = None

    def get_filled_matrix(self, color):
        """
        Baut eine Liste (Höhe und Breite gemäss Objekt Initialisierung, gefült mit "color"
        :param color: die Farbe (r, g, b) die als Füllung benutzt wird
        :type color: iterable Länge 3 ,mit Farben RED, GREEN, BLAU
        :return: Array[Heigh][Width][color r, g, b]
        :rtype: list
        """
        # Benutz "list comprehension". die [:] nach die Listen forciert eine kopie.
        return [[color[:] for x in range(self.width)][:] for y in range(self.height)]

    def init_rgb_matrix(self):
        """
        Initialisierung der 8 x 8 x 3 Matrix für die vereinfachte Farbzuweisung.
        Dimension 8 x 8 ist fix definiert!
        """
        return self.get_filled_matrix(self.default_color)

    def open_interface(self):
        """
        Öffnen der entsprechenden Schnittstelle, z.B. UART
        """
        self.gui = Gui(self.width, self.height)
        self.gui.start()
        webbrowser.open('http://localhost:8000/LedArray.html', new=2)

    def close_interface(self):
        """
        Schliessen der entsprechenden Schnittstelle, z.B. UART
        """
        self.gui.end()

    def write2rgb(self):
        """
        Entsprechende Matrix auf der RGB-Matrix darstellen.
        1. Transformation
        2. Werte auf Schnittstelle schreiben
        """
        self.gui.set_array_colors(self.rgb_matrix)


class Gui(threading.Thread):
    def __init__(self, width, height):
        '''
        Creating the GUI
        :return:
        :rtype:
        '''
        threading.Thread.__init__(self)

        self.connected = False
        self.led_array_listener = []
        self.connection_state_listener = []
        self.width = width
        self.height = height

        # Register listener in the LocalCGIHTTPRequestHandler class
        LocalCGIHTTPRequestHandler.local_cgi_script["connection_status"] = self.add_connection_state_listener
        LocalCGIHTTPRequestHandler.local_cgi_script["led_array"] = self.add_led_array_listener

        # Create server instance
        self.https = ThreadingHTTPServer(('', 8000), LocalCGIHTTPRequestHandler)

        self.led_array = []
        self.html_led_array = 'EMPTY'

    def run(self):
        self.set_connected(True)
        self.https.serve_forever()

    def end(self):
        self.set_connected(False)
        self.https.shutdown()
        self.https.server_close()

    def set_array_colors(self, led_array):
        self.led_array = deepcopy(led_array)
        html = ['<div id="ledArray2">']
        for row in self.led_array:
            html.append('<div class="line">')
            for r, g, b in row:
                html.append(f'<div class="led" style="background-color:rgb({r}, {g}, {b});"></div>')

            html.append('</div>')

        html.append('</div>')

        self.html_led_array = ''.join(html)
        self.inform_led_array_listener()

    def add_connection_state_listener(self, q):
        self.connection_state_listener.append(q)
        self.inform_connection_state_listener(q)

    def add_led_array_listener(self, q):
        self.led_array_listener.append(q)
        self.inform_led_array_listener(q)

    @staticmethod
    def get_color_in_hex(color):
        c = '#'
        for pure in color:
            c += f'{pure:02X}'[-2:]

        return c

    def inform_connection_state_listener(self, q=None):
        if q:
            lst = [q]
        else:
            lst = self.connection_state_listener

        for l in lst:
            l.put("Connected" if self.connected else "NOT Connected")
            if not self.connected:
                l.put("#QUIT#")

    def inform_led_array_listener(self, q=None):
        if q:
            lst = [q]
        else:
            lst = self.led_array_listener

        for l in lst:
            if not self.connected:
                l.put("#QUIT#")
            else:
                l.put(self.html_led_array)

    def set_connected(self, connected):
        self.connected = connected
        self.inform_connection_state_listener()
        self.inform_led_array_listener()


class LocalCGIHTTPRequestHandler(CGIHTTPRequestHandler):

    def is_cgi(self):
        """Test whether self.path corresponds to a local CGI script or a CGI script.

        Returns True and updates the cgi_info attribute to the tuple
        (dir, rest) if self.path requires running a CGI script.
        Returns False otherwise.

        Returns True and set local_cgi to True if it's a local CI script.

        If any exception is raised, the caller should assume that
        self.path was rejected as invalid and act accordingly.

        The default implementation tests whether the normalized url
        path begins with one of the strings in self.cgi_directories
        (and the next character is a '/' or the end of the string).

        """
        collapsed_path = _url_collapse_path(self.path)
        dir_sep = collapsed_path.find('/', 1)
        head, tail = collapsed_path[:dir_sep], collapsed_path[dir_sep+1:]
        if head in self.local_cgi_path:
            self.cgi_info = head, tail
            self.local_cgi = True
            return True
        else:
            self.local_cgi = False
            return super().is_cgi()

    local_cgi_path = ['/local_cgi']
    local_cgi_script = dict()

    def run_cgi(self):
        """Execute a local CGI script. Is it a standard CGI script, delegate to super"""
        if not self.local_cgi:
            super().run_cgi()

        self.send_response(HTTPStatus.OK, "Script output follows")
        self.flush_headers()

        # The function name should directly follow the path, before some query
        dir, rest = self.cgi_info
        # supress "/"
        if rest[0] == '/':
            rest = rest[1:]

        func, _, query = rest.partition('?')

        if func not in self.local_cgi_script:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                f"No such CGI script ({func})")
            return

        nb = self.wfile.write(b"Content-Type: text/event-stream\n\n")
        self.log_message(f"{func} // Send content type: {nb} bytes")
        self.wfile.flush()

        queue = Queue()
        queue_registar = self.local_cgi_script[func]
        queue_registar(queue)

        while True:
            self.log_message(f"{func} // Wait for Queue")
            try:
                msg = queue.get()

                if msg == "#QUIT#":
                    self.log_message(f"{func} // Exit event messenger")
                    return
                else:
                    nb = self.wfile.write(bytes("data: " + msg, 'utf-8'))
                    self.wfile.write(b"\n\n")
                    self.log_message(f"{func} // Send data: {nb} bytes")
                    # self.log_message(f"{func} // data= {msg}")
                    self.wfile.flush()
            except Exception:
                pass


if __name__ == "__main__":
    rgb = RGBBasis(default_color=[100, 100, 100])
    print("Open interface")
    rgb.open_interface()
    print("write2rgb")
    rgb.write2rgb()
    print("sleep")
    time.sleep(1)
    rgb.rgb_matrix = rgb.get_filled_matrix([100, 0, 0])
    rgb.write2rgb()
    print("close interface")
    rgb.close_interface()
