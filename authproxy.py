import socketserver
import socket
import select
import base64
import getpass
import configparser

#Ref:
#https://tools.ietf.org/rfc/rfc7230.txt

class ProxyHandler(socketserver.BaseRequestHandler):
    timeout_relay = 3600 #Time for neither party to send any data to timeout the connection
    timeout_socket = 5 # Used by create_connection() as time for new connection to timeout
    #N.B. recv() also use timeout_socket, but it is protected by select()
    #N.B. Besides timeout_socket, a ?system-wide connection timeout is additionally in place

    
    parentProxyAdr = ("127.0.0.1","8888")
    authString = ''.encode()

    @classmethod
    def setuser(cls,user):
        if user != '':
            cls.authString = ('Proxy-Authorization: Basic %s\r\n' % base64.b64encode((user+":"+getpass.getpass()).encode()).decode('ascii')).encode()

    @classmethod
    def setproxy(cls,addr,port):
        cls.parentProxyAdr = (addr,port)
    
    def handle(self):
        L = self.request
        R = socket.create_connection(self.parentProxyAdr, timeout=self.timeout_socket)

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
                else not rlist:
                    print('408 Timeout: %s %s' % (cmd, target)) #Relay timeout
                    #TODO Response 408
                    return
                
        except ConnectionResetError as e:
            raise
        except (socket.timeout,TimeoutError): #timeout from recv; socket.timeout -> exceeded timeout_socket, TimeoutError -> exceeded ?system-wide timeout
            raise Exception("Should NOT happen") #Should be protected by 'select' function
        except Exception as e:
            raise
        finally:
            L.close()
            R.close()

            #TODO Consider Response 408 Request Timeout with header: close

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
    
    ProxyHandler.setproxy(config['DEFAULT']['address'], config['DEFAULT']['port'])
    ProxyHandler.setuser(config['DEFAULT']['user'])

    #server = socketserver.TCPServer(("localhost",8080), ProxyHandler)
    server = socketserver.ThreadingTCPServer(("localhost",8080), ProxyHandler)
    server.serve_forever()
                                

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
