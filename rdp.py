#T. Pires - CSC361 P2 (rdp.py) - 2023-02-10
#Last Updated - 2023-03-09

#RDP Implementation

#NOTE: Wait a few seconds in between requests involving large files; longer post-run program overhead.

import datetime
import select
import socket
import sys
import time as tl

if sys.argv[2] != "8888":
    print("ERROR: Invalid port. Use UDP port 8888.")
    exit(0)
    
if sys.argv[1] == "h1": #For faster invokation on picolab
    sys.argv[1] = "192.168.1.100"
    
udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Initialize "UDP" socket
udpSocket.setblocking(0)
udpSocket.bind((sys.argv[1], 8888))

echoServer = ("10.10.1.100", 8888) #Echo server hardcoded to h2 on Picolab. Can be change if off-site.

globalIndex = 0

windowSlots = 2 #Change this to change window size program wide
timeout = 1 #Change this to change timeout value program wide (value in seconds). Less than 1 second not recommended, especially for large congestion windows.

readFile = open(sys.argv[3], "r")
writeFile = open(sys.argv[4], "w")

rdpSent = 0 #Amount of RDP packets sent
rdpReceived = 0 #Amount of RDP packets received

indexBuffer = [] #Stores sequence numbers of dat packets

synBuffer = {}
synTimeout = {}

ackBuffer = {}
ackTimeout = {}

datBuffer = {}
datTimeout = {}
datPayload = {} #Stores unpacked message paylods

finBuffer = {}
finTimeout = {}

synReceived = 0 #SYN handshake switch
initialAckReceived = 0 #Initial ACK handshake switch
eofReached = 0 #EOF switch
finSent = 0 #FIN sent switch
finalAckSent = 0 #Final ACK sent switch

while True:

    readable, writable, exceptional = select.select([udpSocket], [udpSocket], [udpSocket])
    
    for udpSocket in readable:

        message = udpSocket.recv(2048).decode() #1024 for header, 1024 for payload
        
        if synReceived == 0: #Unreachable after switch is "switched"; ensure no data is sent before SYN handshake
            
            index = 0
            
            rdpReceived += 1
            
            currentTime = datetime.datetime.now()
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Receive; SYN; Sequence: 0; Length: 0")
            print(log)
            
            del synBuffer[0]
            del synTimeout[0]
            
            synReceived = 1 #Done dealing with SYN handshake; send initial ACK handshake
            
            index = 1
            packet = f"ACK\nAcknowledgment: 1\nWindow: {windowSlots*1024}\n\n".encode()
            
            udpSocket.sendto(packet, echoServer)
            
            rdpSent += 1
            
            currentTime = datetime.datetime.now()
            timeoutTime = currentTime + datetime.timedelta(0, timeout)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; ACK; Acknowledgment: 1; Window: {windowSlots*1024}")
            print(log)
            
            ackBuffer[index] = packet
            ackTimeout[index] = timeoutTime
            
        elif message[0:3] == "ACK":

            if initialAckReceived == 0: #Unreachable after switch is "switched"; ensure no data is sent before initial ACK handshake
                
                rdpReceived += 1
                
                currentTime = datetime.datetime.now()
                
                log = currentTime.strftime(f"%a %b %d %X PDT %Y: Receive; ACK; Acknowledgment: 1; Window: {windowSlots*1024}")
                print(log)
                
                del ackBuffer[1]
                del ackTimeout[1]
                
                initialAckReceived = 1
            else:
                
                packetLines = message.splitlines(1)
                
                indexLine = packetLines[1]
                index = int(indexLine[16:-1])
                
                rdpReceived += 1
                
                currentTime = datetime.datetime.now()

                log = currentTime.strftime(f"%a %b %d %X PDT %Y: Receive; ACK; Acknowledgment: {index}; Window: {windowSlots*1024}")
                print(log)
                
                del ackBuffer[index]
                del ackTimeout[index]
            
                if finalAckSent == 1:
                    indexSorted = sorted(indexBuffer)
                    
                    for index in indexSorted:
                        writeFile.write(datPayload[index])
                        
                    readFile.close()
                    writeFile.close()
                    
                    exit(0)
        elif message[0:3] == "DAT":
            
            windowSlots += 1
            
            packetLines = message.splitlines(1)
            
            indexLine = packetLines[1]
            index = int(indexLine[10:-1])
            indexBuffer.append(index)
            
            headerLength = len(packetLines[0]) + len(packetLines[1]) +len(packetLines[2]) +len(packetLines[3])
            payload = message[headerLength:-1]
            if len(payload) > 1024: #Fail-safe for duplicated packet
                payload = message[headerLength:headerLength + 1024]
            datPayload[index] = payload
            
            rdpReceived += 1 
            
            currentTime = datetime.datetime.now()
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Receive; DAT; Sequence: {index}; Length: {len(payload)}")
            print(log)
            
            del datBuffer[index]
            del datTimeout[index]
            
            index += len(datPayload[index])
            packet = f"ACK\nAcknowledgment: {index}\nWindow: {windowSlots*1024}\n\n".encode()
            
            udpSocket.sendto(packet, echoServer)
            
            rdpSent += 1
            
            currentTime = datetime.datetime.now()
            timeoutTime = currentTime + datetime.timedelta(0, timeout)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; ACK; Acknowledgment: {index}; Window: {windowSlots*1024}")
            print(log)
            
            ackBuffer[index] = packet
            ackTimeout[index] = timeoutTime
            
        elif message[0:3] == "FIN":
            
            index = globalIndex
            
            currentTime = datetime.datetime.now()
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Receive; FIN; Sequence: {index}; Length: 0")
            print(log)
            
            del finBuffer[index]
            del finTimeout[index]
            
            globalIndex += 1
            
            index = globalIndex
            packet = f"ACK\nAcknowledgment: {index}\nWindow: {windowSlots*1024}\n\n".encode()
            
            udpSocket.sendto(packet, echoServer)

            currentTime = datetime.datetime.now()
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; ACK; Acknowledgment: {index}; Window: {windowSlots*1024}")
            print(log)
            
            ackBuffer[index] = packet
            ackTimeout[index] = timeoutTime

            finalAckSent = 1
    for udpSocket in writable:

        if rdpSent == 0: #If SYN hasn't been sent yet, send it
            
            index = globalIndex
            packet = "SYN\nSequence\nLength: 0\n\n".encode()
            
            udpSocket.sendto(packet, echoServer)
            
            rdpSent += 1
            
            currentTime = datetime.datetime.now()
            timeoutTime = currentTime + datetime.timedelta(0, timeout)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; SYN; Sequence: 0; Length: 0")
            print(log)
            
            synBuffer[index] = packet
            synTimeout[index] = timeoutTime
            
            globalIndex += 1
        elif eofReached == 1 and rdpSent == rdpReceived and finSent == 0:
            
            index = globalIndex
            packet = f"FIN\nSequence: {index}\nLength: 0\n\n".encode()

            udpSocket.sendto(packet, echoServer)

            currentTime = datetime.datetime.now()
            timeoutTime = currentTime + datetime.timedelta(0, timeout)

            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; FIN; Sequence: {index}; Length: 0")
            print(log)

            finBuffer[index] = packet
            finTimeout[index] = timeoutTime
            
            finSent = 1
        elif initialAckReceived == 1 and windowSlots >= 1:
            
            windowSlots -= 1
            payload = readFile.read(1024)

            if len(payload) == 0:
                windowSlots += 1
                eofReached = 1
                pass
            else:
                index = globalIndex
                packet = f"DAT\nSequence: {index}\nLength: {len(payload)}\n\n{payload}\n".encode()
            
                udpSocket.sendto(packet, echoServer)
            
                rdpSent += 1
            
                currentTime = datetime.datetime.now()
                timeoutTime = currentTime + datetime.timedelta(0, timeout)
            
                log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; DAT; Sequence: {index}; Length: {len(payload)}")
                print(log)
            
                datBuffer[index] = packet
                datTimeout[index] = timeoutTime
            
                globalIndex += len(payload)
        else:
            pass
        
    for udpSocket in exceptional:
        pass
    
    for index, time in synTimeout.items(): #Ensure syn packet hasn't timed out
        
        currentTime = datetime.datetime.now()
        
        if currentTime >= time:
            
            synTimeout[index] = time + datetime.timedelta(0, timeout)
            packet = synBuffer[index]
            
            udpSocket.sendto(packet, echoServer)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; RST; Sequence: {index}")
            print(log)
    
    for index, time in ackTimeout.items(): #Ensure ack packets haven't timed out
        
        currentTime = datetime.datetime.now()
        
        if currentTime >= time:
            
            ackTimeout[index] = time + datetime.timedelta(0, timeout)
            packet = ackBuffer[index]
            
            udpSocket.sendto(packet, echoServer)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; RST; Acknowledgment: {index}")
            print(log)
    
    for index, time in datTimeout.items(): #Ensure dat packets haven't timed out
        
        currentTime = datetime.datetime.now()
        
        if currentTime >= time:
            
            datTimeout[index] = time + datetime.timedelta(0, timeout)
            packet = datBuffer[index]
            
            udpSocket.sendto(packet, echoServer)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; RST; Sequence: {index}")
            print(log)
    
    for index, time in finTimeout.items(): #Ensure fin packet hasn't timed out
        
        currentTime = datetime.datetime.now()
        
        if currentTime >= time:
            
            finTimeout[index] = time + datetime.timedelta(0, timeout)
            packet = finBuffer[index]
            
            udpSocket.sendto(packet, echoServer)
            
            log = currentTime.strftime(f"%a %b %d %X PDT %Y: Send; RST; Sequence: {index}")
            print(log)