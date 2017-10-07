import functools
import socketserver
import socket
import select
import base64
import getpass
import configparser
import logging
import threading

logger = logging.getLogger(__name__)
#Ref:
#https://tools.ietf.org/rfc/rfc7230.txt

class ProxyHandler(socketserver.BaseRequestHandler):
    timeout_relay = 3600 #Time for neither party to send any data to timeout the connection
    timeout_socket = 5 # Used by create_connection() as time for new connection to timeout
    #N.B. recv() also use timeout_socket, but it is protected by select()
    #N.B. Besides timeout_socket, a ?system-wide connection timeout is additionally in place

    def __init__(self, parent_addr, parent_port, parent_user, parent_pass, *args, **kwargs):
        self.parentProxyAdr = (parent_addr, str(parent_port))
        if parent_user != '':
            self.authString = ('Proxy-Authorization: Basic %s\r\n' % base64.b64encode((parent_user+":"+parent_pass).encode()).decode('ascii')).encode()
        else:
            self.authString = ''.encode()
        super().__init__(*args, **kwargs)

    def handle(self):
        L = self.request
        try:
            R = socket.create_connection(self.parentProxyAdr, timeout=self.timeout_socket)
        except socket.timeout:
            print('Cannot connect to parent proxy')
            return
        
        sockets = [L,R]
        last = None
        intercept = True
        try:
            while True:
                rlist, wlist, xlist = select.select(sockets, [], sockets, self.timeout_relay)
                if rlist:
                    for source in rlist:
                        data = source.recv(8192)
                        if not data: #Connection closed
                            return

                        dest = L if source is R else R
                        if intercept:
                            if source != last:
                                last = source
                                if source is L: #If this is the first packet from Local
                                    firstCRCL = data.find(b"\n",2);
                                    if firstCRCL == -1:
                                        print('Error 414: ' + repr(data))
                                        #TODO Response 414 URI Too Long
                                        return

                                    try:
                                        cmd = data[:firstCRCL].decode().strip()
                                        #print(repr(cmd))
                                        cmd, target, version = cmd.split(" ")
                                    except (ValueError, UnicodeDecodeError) as e:
                                        print('Error 400: ' + repr(data))
                                        #TODO Response 400 Bad Request
                                        return
                                    if cmd == "CONNECT":
                                        intercept = False

                                    dest.sendall(data[:firstCRCL+1])
                                    dest.sendall(self.authString)
                                    dest.sendall(data[firstCRCL+1:])

                                    if target == "/open.pac":
                                        if cmd == "GET":
                                            with open('pac.txt', 'rb') as f:
                                                source.sendall(b"HTTP/1.1 200 OK\r\n\r\n") #TODO Connection-close header
                                                data = True
                                                while data:
                                                    data = f.read(8192)
                                                    source.sendall(data)
                                            return
                                        raise Exception("Should NOT happen")

                                    continue

                        dest.sendall(data) #Relay as-is if not intercepted
                elif xlist:
                    print(len(rlist)) #Theoretically can happen but i have never seen
                    print(len(wlist))
                    print(len(xlist))
                    print(xlist[0].recv(8192))
                    return
                else:
                    print('408 Timeout: %s %s' % (cmd, target)) #Relay timeout
                    #TODO Response 408
                    return

        except ConnectionResetError as e: #WinError 10054: An existing connection was forcibly closed by the remote host
            return
        except (socket.timeout,TimeoutError): #timeout from recv; socket.timeout -> exceeded timeout_socket, TimeoutError -> exceeded ?system-wide timeout
            raise Exception("Should NOT happen") #Should be protected by 'select' function
        except Exception as e:
            raise
        finally:
            L.close()
            R.close()

            #TODO Consider Response 408 Request Timeout with header: close

class AuthProxy():
    def __init__(self, parent_addr, parent_port, parent_user, parent_pass):
        # server = socketserver.TCPServer(("localhost",8080), ProxyHandler)
        self.server = socketserver.ThreadingTCPServer(
            ("localhost", 8888),
            functools.partial(ProxyHandler, parent_addr, parent_port, parent_user, parent_pass))
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.shutdown()
        self.server.server_close()



def main():
    _CONFIG_FILENAME = 'authproxy.ini'
    config = configparser.ConfigParser()
    config.read(_CONFIG_FILENAME)
    try:
        if config['DEFAULT']['address'] == '' or config['DEFAULT']['port'] == '' or config['DEFAULT']['user'] == '':
            raise KeyError
    except KeyError:
        config['DEFAULT']['address'] = ''
        config['DEFAULT']['port'] = ''
        config['DEFAULT']['user'] = ''
        with open(_CONFIG_FILENAME, 'w') as f:
            config.write(f)
        print('No valid setting from authproxy.ini. Terminating.')
        return

    with AuthProxy(config['DEFAULT']['address'],
                   config['DEFAULT']['port'],
                   config['DEFAULT']['user'], getpass.getpass()):
        input()

if __name__ == '__main__':
    main()


#Experiments

##def test():
##    from threading import Thread
##    import time
##
##    addr = ("localhost",8888)
##
##    def serve_one():
##        with socket.socket() as listener:
##            listener.bind(addr)
##            listener.listen(1)
##            with listener.accept()[0] as R:
##                print(len(R.recv(8192)))
##                time.sleep(10)
##                pass
##
##    thread = Thread(target = serve_one)
##    thread.start()
##    try:
##        with socket.create_connection(('127.0.0.1', 8888), timeout=1) as L:
##            rlist, wlist, xlist = select.select([L], [], [L], 30)
##            print(rlist, wlist, xlist)
##            print(len(L.recv(8192)))
##            #time.sleep(30)
##            #L.sendall(b'Hellow World!')
##    except TimeoutError:
##        print('system timeout')
##        raise
##    except socket.timeout:
##        print('socket timeout')
##        raise
##    #thread.join()
##
##test()
