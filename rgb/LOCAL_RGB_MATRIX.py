# ======================
# imports
# ======================
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import HTTPServer, CGIHTTPRequestHandler, _url_collapse_path
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

        self.default_color = default_color

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

        # Create server instance
        LocalCGIHTTPRequestHandler.local_cgi_script["connection_status"] = self.add_connection_state_listener

        self.https = HTTPServer(('', 8000), LocalCGIHTTPRequestHandler)

        self.led_array = []

    def run(self):
        self.set_connected(True)
        self.https.serve_forever()

    def end(self):
        self.set_connected(False)
        self.https.shutdown()
        self.https.server_close()

    def set_array_colors(self, led_array):
        for r, row in enumerate(self.led_array):
            for c, label in enumerate(row):
                color = led_array[r][c]
                label['background'] = self.get_color_in_hex(color)

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
        pass

    def set_connected(self, connected):
        self.connected = connected
        self.inform_connection_state_listener()


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
        self.log_message(f"Send content type: {nb} bytes")
        self.wfile.flush()

        queue = Queue()
        queue_registar = self.local_cgi_script[func]
        queue_registar(queue)

        while True:
            self.log_message(f"Wait for Queue")
            msg = queue.get()

            if msg == "#QUIT#":
                self.log_message(f"Exit event messenger")
                return
            else:
                nb = self.wfile.write(bytes("data: " + msg, 'utf-8'))
                self.wfile.write(b"\n\n")
                self.log_message(f"Send data: {nb} bytes")
                self.wfile.flush()

        # dir, rest = self.cgi_info
        # path = dir + '/' + rest
        # i = path.find('/', len(dir)+1)
        # while i >= 0:
        #     nextdir = path[:i]
        #     nextrest = path[i+1:]
        #
        #     scriptdir = self.translate_path(nextdir)
        #     if os.path.isdir(scriptdir):
        #         dir, rest = nextdir, nextrest
        #         i = path.find('/', len(dir)+1)
        #     else:
        #         break
        #
        # # find an explicit query string, if present.
        # rest, _, query = rest.partition('?')
        #
        # # dissect the part after the directory name into a script name &
        # # a possible additional path, to be stored in PATH_INFO.
        # i = rest.find('/')
        # if i >= 0:
        #     script, rest = rest[:i], rest[i:]
        # else:
        #     script, rest = rest, ''
        #
        # scriptname = dir + '/' + script
        # scriptfile = self.translate_path(scriptname)
        # if not os.path.exists(scriptfile):
        #     self.send_error(
        #         HTTPStatus.NOT_FOUND,
        #         "No such CGI script (%r)" % scriptname)
        #     return
        # if not os.path.isfile(scriptfile):
        #     self.send_error(
        #         HTTPStatus.FORBIDDEN,
        #         "CGI script is not a plain file (%r)" % scriptname)
        #     return
        # ispy = self.is_python(scriptname)
        # if self.have_fork or not ispy:
        #     if not self.is_executable(scriptfile):
        #         self.send_error(
        #             HTTPStatus.FORBIDDEN,
        #             "CGI script is not executable (%r)" % scriptname)
        #         return
        #
        # # Reference: http://hoohoo.ncsa.uiuc.edu/cgi/env.html
        # # XXX Much of the following could be prepared ahead of time!
        # env = copy.deepcopy(os.environ)
        # env['SERVER_SOFTWARE'] = self.version_string()
        # env['SERVER_NAME'] = self.server.server_name
        # env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        # env['SERVER_PROTOCOL'] = self.protocol_version
        # env['SERVER_PORT'] = str(self.server.server_port)
        # env['REQUEST_METHOD'] = self.command
        # uqrest = urllib.parse.unquote(rest)
        # env['PATH_INFO'] = uqrest
        # env['PATH_TRANSLATED'] = self.translate_path(uqrest)
        # env['SCRIPT_NAME'] = scriptname
        # if query:
        #     env['QUERY_STRING'] = query
        # env['REMOTE_ADDR'] = self.client_address[0]
        # authorization = self.headers.get("authorization")
        # if authorization:
        #     authorization = authorization.split()
        #     if len(authorization) == 2:
        #         import base64, binascii
        #         env['AUTH_TYPE'] = authorization[0]
        #         if authorization[0].lower() == "basic":
        #             try:
        #                 authorization = authorization[1].encode('ascii')
        #                 authorization = base64.decodebytes(authorization).\
        #                                 decode('ascii')
        #             except (binascii.Error, UnicodeError):
        #                 pass
        #             else:
        #                 authorization = authorization.split(':')
        #                 if len(authorization) == 2:
        #                     env['REMOTE_USER'] = authorization[0]
        # # XXX REMOTE_IDENT
        # if self.headers.get('content-type') is None:
        #     env['CONTENT_TYPE'] = self.headers.get_content_type()
        # else:
        #     env['CONTENT_TYPE'] = self.headers['content-type']
        # length = self.headers.get('content-length')
        # if length:
        #     env['CONTENT_LENGTH'] = length
        # referer = self.headers.get('referer')
        # if referer:
        #     env['HTTP_REFERER'] = referer
        # accept = []
        # for line in self.headers.getallmatchingheaders('accept'):
        #     if line[:1] in "\t\n\r ":
        #         accept.append(line.strip())
        #     else:
        #         accept = accept + line[7:].split(',')
        # env['HTTP_ACCEPT'] = ','.join(accept)
        # ua = self.headers.get('user-agent')
        # if ua:
        #     env['HTTP_USER_AGENT'] = ua
        # co = filter(None, self.headers.get_all('cookie', []))
        # cookie_str = ', '.join(co)
        # if cookie_str:
        #     env['HTTP_COOKIE'] = cookie_str
        # # XXX Other HTTP_* headers
        # # Since we're setting the env in the parent, provide empty
        # # values to override previously set values
        # for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH',
        #           'HTTP_USER_AGENT', 'HTTP_COOKIE', 'HTTP_REFERER'):
        #     env.setdefault(k, "")
        #
        # self.send_response(HTTPStatus.OK, "Script output follows")
        # self.flush_headers()
        #
        # decoded_query = query.replace('+', ' ')
        #
        # if self.have_fork:
        #     # Unix -- fork as we should
        #     args = [script]
        #     if '=' not in decoded_query:
        #         args.append(decoded_query)
        #     nobody = nobody_uid()
        #     self.wfile.flush() # Always flush before forking
        #     pid = os.fork()
        #     if pid != 0:
        #         # Parent
        #         pid, sts = os.waitpid(pid, 0)
        #         # throw away additional data [see bug #427345]
        #         while select.select([self.rfile], [], [], 0)[0]:
        #             if not self.rfile.read(1):
        #                 break
        #         if sts:
        #             self.log_error("CGI script exit status %#x", sts)
        #         return
        #     # Child
        #     try:
        #         try:
        #             os.setuid(nobody)
        #         except OSError:
        #             pass
        #         os.dup2(self.rfile.fileno(), 0)
        #         os.dup2(self.wfile.fileno(), 1)
        #         os.execve(scriptfile, args, env)
        #     except:
        #         self.server.handle_error(self.request, self.client_address)
        #         os._exit(127)
        #
        # else:
        #     # Non-Unix -- use subprocess
        #     import subprocess
        #     cmdline = [scriptfile]
        #     if self.is_python(scriptfile):
        #         interp = sys.executable
        #         if interp.lower().endswith("w.exe"):
        #             # On Windows, use python.exe, not pythonw.exe
        #             interp = interp[:-5] + interp[-4:]
        #         cmdline = [interp, '-u'] + cmdline
        #     if '=' not in query:
        #         cmdline.append(query)
        #     self.log_message("command: %s", subprocess.list2cmdline(cmdline))
        #     try:
        #         nbytes = int(length)
        #     except (TypeError, ValueError):
        #         nbytes = 0
        #     p = subprocess.Popen(cmdline,
        #                          stdin=subprocess.PIPE,
        #                          stdout=subprocess.PIPE,
        #                          stderr=subprocess.PIPE,
        #                          env = env
        #                          )
        #     if self.command.lower() == "post" and nbytes > 0:
        #         data = self.rfile.read(nbytes)
        #     else:
        #         data = None
        #     # throw away additional data [see bug #427345]
        #     while select.select([self.rfile._sock], [], [], 0)[0]:
        #         if not self.rfile._sock.recv(1):
        #             break
        #     stdout, stderr = p.communicate(data)
        #     self.wfile.write(stdout)
        #     if stderr:
        #         self.log_error('%s', stderr)
        #     p.stderr.close()
        #     p.stdout.close()
        #     status = p.returncode
        #     if status:
        #         self.log_error("CGI script exit status %#x", status)
        #     else:
        #         self.log_message("CGI script exited OK")



if __name__ == "__main__":
    rgb = RGBBasis(default_color=[100, 100, 100])
    print("Open interface")
    rgb.open_interface()
    print("write2rgb")
    rgb.write2rgb()
    print("sleep")
    time.sleep(10)
    print("close interface")
    rgb.close_interface()
