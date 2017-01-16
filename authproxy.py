import socketserver
import socket
import select
import base64
import getpass


#Ref: https://tools.ietf.org/rfc/rfc7230.txt


class ProxyHandler(socketserver.BaseRequestHandler):
    timeout = 5
    parentProxyAdr = ("__PROXY_URL_HERE__","8080")
    authString = ('Proxy-Authorization: Basic %s\r\n' % base64.b64encode(("__USER_NAME_NERE__:"+getpass.getpass()).encode()).decode('ascii')).encode()
    
    def handle(self):
        L = self.request
        R = socket.create_connection(self.parentProxyAdr, timeout=self.timeout)

        source = L
        dest = R

        try:
            data = source.recv(8192)
        except ConnectionResetError as e:
            if source == L:
                #TODO Consider Response 408 Request Timeout
                #Header: close
                pass
            else:
                #Drop
                pass
            return

        
        firstCRCL = data.find(b"\n",2);
        if firstCRCL == -1:
            if source == L:
                #TODO Response 414 URI Too Long
                pass
            else:
                #Drop
                pass

        
        cmd = data[:firstCRCL].decode().strip()
        try:
            if source == L:
                cmd, target, version = cmd.split(" ")
            else:
                version, status, phrase = cmd.split(" ",2)
        except ValueError as e:
            if souce == L:
                #TODO Response 400 Bad Request
            else:
                #Drop
            return
        #TODO Enforce HTTP/1.1?
        
        lastCRCL = data.find(b"\r\n\r\n", firstCRCL)
        if lastCRCL == -1:
            if source == L:
                #TODO Response 400 Bad Request
                return
            else:
                #Drop
                pass

        def getHeader(name):
            len_offset = data.find(b"\r\n%s:" % name, firstCRCL, lastCRCL)
            if len_offset == -1:
                return None
            len_end = data.find(b"\r\n", len_offset+2, lastCRCL+2)
            return data[len_offset+len(name)+3:len_end].decode().strip()


        transfer_encoding = getHeader(b"Transfer-Encoding")
        if transfer_encoding:
            transfer_encoding.split(",").pop().strip()
        else:
            content_length = getHeader(b"Content-Length")
            if content_length:
                content_length = int(content_length)
                #if not parsable:
                    #can try recover comma seperated same value
                    #if source == L:
                        #Response 400 Bad Request
                        #Drop
                    #else
                        #Response 502 Bad Gateway to client
                        #Drop
            
        
        b"Content-Range"
        b"Trailer"

        if source == L:
            #if transfer_encoding
                #if transfer_encoding == "chunked"
                    #sendByChunk
                #else
                    #Response 400 Bad Request
                    #Drop
            #elif content_length
                #sendByLength
            #else
                #sendNoBody
                
            
            pass
        else:
            #if HEAD
                #sendNoBody
            #elif [204,304].count(int(status))!=0
                #sendNoBody
            ##???if status[0] == 1:???
                ##sendNoBody
            #elif CONNECT && status[0] == 2
                #tunnel
            #elif transfer_encoding
                #if transfer_encoding == "chunked"
                    #sendByChunk
                #else
                    #sendAll
            #elif content_length
                #sendByLength        
            #else
                #sendAll
            pass

        def sendHeader():
            dest.sendall(data[:firstCRCL+1])
            dest.sendall(self.authString)
            dest.sendall(data[firstCRCL+1:lastCRCL+4])
            return data[lastCRCL+4:]

        #discard extra data after content length
        
        def tunnel():
            dest.sendall(sendHeader())
            
            sockets = [L,R]
            while True:
                rlist, wlist, xlist = select.select(sockets, [], sockets, self.timeout)
                if xlist or not rlist:
                    #Drop
                for source in rlist:
                    dest = L if source is R else R
                    data = source.recv(8192)
                    if not data:
                        #Drop               
                    dest.sendall(data)
                    #try:
                    #    print(data.decode("utf-8", "ignore"))
                    #except Exception as e:
                    #    pass

        def sendAll():
            tunnel()
            pass

        def sendByLength(length):
            data = sendHeader()
            while True:
                dest.sendall(data[:length])
                length -= len(data)
                if length <= 0:
                    break
                data = source.recv(8192)
                
        
        def sendNoBody():
            if len(data) - lastCRCL - 4 > 0:
                ##Response 411 Length Required
                ##Drop
                pass
            sendHeader()

        def sendByChunk():
            data = sendHeader()
            while True:
                while True:
                    firstCRCL = data.find(b"\r\n");
                    if firstCRCL != -1:
                        break
                    data += source.recv(8192)
                chunk_size = int(data[:firstCRCL].split(";"), 16)
                length = firstCRCL+2+chunk_size+2

                while True:
                    dest.sendall(data[:length])
                    data = data[length:]
                    length -= len(data)
                    if length <= 0:
                        break
                    data += source.recv(8192)
                    
                if chunk_size == 0
                    break;

            while True:
                lastCRCL = data.find(b"\r\n\r\n")
                if lastCRCL != -1:
                     break
                data += source.recv(8192)
            dest.sendall(data[:lastCRCL+4])
            
                
            
            
                
            
            
        
        
server = socketserver.TCPServer(("localhost",8080), ProxyHandler)
server.serve_forever()
                                

