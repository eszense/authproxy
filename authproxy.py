from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import http.client
import getpass
import base64
import socket
from socketserver import ThreadingMixIn
import threading
import inspect
import select

class ProxyRequestHandler(BaseHTTPRequestHandler):
    timeout = 5
    parentProxy = "__PROXY_URL_HERE__"
    
    parentProxyAdr = tuple(parentProxy.split(":"))
    authString = 'Basic %s' % base64.b64encode(("__USER_NAME_NERE__:"+getpass.getpass()).encode()).decode('ascii')
    
    def do_GET(self):
        self.do_CMD()
    def do_POST(self):
        self.do_CMD()
    def do_HEAD(self):
        self.do_CMD()
    
    def do_CMD(self):
        L = self
        L_headers = dict(L.headers)
        L_headers['Proxy-Authorization'] = self.authString

        L_content_length = int(L.headers.get('Content-Length', 0))
        L_body = L.rfile.read(L_content_length)
    
        conn = http.client.HTTPConnection(self.parentProxy, timeout=self.timeout)
        conn.request(L.command, L.path, L_body, L_headers)
        R = conn.getresponse()
        L.send_response(R.status)
        R_headers = R.getheaders()
        for header, value in R_headers:
            L.send_header(header, value)
        L.end_headers()
        L.flush_headers()
        L.wfile.write(R.read())

    def do_CONNECT(self):
        L = self
        L_headers = dict(L.headers)
        L_headers['Proxy-Authorization'] = self.authString

        R = socket.create_connection(self.parentProxyAdr, timeout=self.timeout)
        R.sendall(bytes(L.requestline+"\r\n", 'utf-8'));
        for name, value in L_headers.items():
            R.sendall(bytes(name+": "+value+"\r\n", 'utf-8'))
        R.sendall(b"\r\n")

        conns = [L.connection, R]
        self.close_connection = 0
        while not self.close_connection:
            rlist, wlist, xlist = select.select(conns, [], conns, self.timeout)
            if xlist or not rlist:
                break
            for r in rlist:
                other = conns[1] if r is conns[0] else conns[0]
                data = r.recv(8192)
                if not data:
                    self.close_connection = 1
                    break
                other.sendall(data)

        
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    def log_message(self,format, *args):
        return
    def log_date_time_string(self):
        return ""

def main():
    server_address = ('127.0.0.1', 8080)
    httpd = ThreadingHTTPServer(server_address,  ProxyRequestHandler)
    sa = httpd.socket.getsockname()
    print("Serving HTTP Proxy on", sa[0], "port", sa[1], "...")
    httpd.serve_forever()
    

if __name__ == '__main__':
    main()
