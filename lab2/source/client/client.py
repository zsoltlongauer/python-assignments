import socket as factory
import functions
import sys
import json

sys.path.append('../encryption')

import knapsack
import solitaire

HOST = 'localhost'
PORT = 30001

class Client:
    def __init__(self, tp):
        self.knap = knapsack.Knapsack(8)
        self.type = tp

        if tp == 0:
            self.clientId = 33301
            self.connectToServer()
            # Selecting which user we want to speak to
            print("Tell me which client you want to speak with:")
            c2Id = int(input())

            self.getPeerKey(c2Id)

            # Checking if we found the client
            while self.peerKey == -1:
                print('There is no such client logged in to the server')
                print("Tell me which client you want to speak with:")
                c2Id = int(input())

                self.getPeerKey(c2Id)

            self.peerKey = functions.stringToIntList(self.peerKey)

            self.startPeerCommunication()

        else:
            self.clientId = 33302
            self.connectToServer()
            self.acceptPeerConnection()

            self.getPeerKey(self.peerId)
            
            self.peerKey = functions.stringToIntList(self.peerKey)

            # Sending ACK
            self.send_msg(self.peerSocket, json.dumps({"ACK" : 1}))

    def initSolitaire(self):
        # Creating the Solitaire encryption tool
        self.sol = solitaire.Solitaire()
        self.sol.phraseShuffle(self.solitairePhrase)

    def connectToServer(self):
        # Connecting the client to the server
        self.socket = factory.socket(factory.AF_INET, factory.SOCK_STREAM)
        server_address = (HOST, PORT)
        self.socket.connect(server_address)

        self.login()
        print('Logged in to keyserver')

    def login(self):
        pkMsg = functions.intListToString(self.knap.publicKey)
        msg = {
            "id" : self.clientId,
            "publicKey" : pkMsg
        }

        # Sending our id and publicKey to the server
        self.send_msg(self.socket, json.dumps(msg))

    def send_msg(self, socket, msg):
        size = len(str(msg))

        while size > 255:
            socket.sendall(bytes([255]))
            size -= 255

        socket.sendall(bytes([size]))
        socket.sendall(msg.encode())

    def read(self, socket):
        # Getting how many bytes we need to read
        n = int.from_bytes(socket.recv(1), 'big')
        length = n

        while n == 255:
            n = int.from_bytes(socket.recv(1), 'big')
            length += n

        # Reading those bytes
        msg = socket.recv(length)

        print('Received:')
        print(msg)

        return msg


    def getPeerKey(self, id):
        # Telling the server which client we want to speak to
        self.peerId = id
        msg = {
            "peer" : id
        }
        self.send_msg(self.socket, json.dumps(msg))

        # Receiving it's public key and addr
        self.peerKey = json.loads(self.read(self.socket).decode('utf-8'))['peer']

    def startPeerCommunication(self):
        # Creating a new socket by which we can speak to the other client
        self.peerSocket = factory.socket(factory.AF_INET, factory.SOCK_STREAM)
        server_address = (HOST, self.peerId)

        # Connecting to the other client
        self.peerSocket.connect(server_address)
        print('Connected to the peer we want to speak with')

        # Sending hello
        print('Sending hello to the other client')
        self.send_msg(self.peerSocket, json.dumps({"peer" : self.clientId}))

        # Waiting for hello
        ack = self.read(self.peerSocket).decode('utf-8')
        print(ack)

        print('Starting conversation')

    def acceptPeerConnection(self):
        # Creating a new socket by which we can speak to the other client
        self.peerConn = factory.socket(factory.AF_INET, factory.SOCK_STREAM)
        self.peerConn.bind((HOST, self.clientId))

        print('Listening for the client that wants to chat')
        self.peerConn.listen()
        # Accept the connection
        self.peerSocket, _ = self.peerConn.accept()
        print('Accepted connection from peer')

        self.peerId = json.loads(self.read(self.peerSocket).decode('utf-8'))['peer']
        print(self.peerId)
        

    def assemblePhrase(self, phrase):
        # Sending the phrase that which we will use in Solitaire encryptions
        formatedPhrase = functions.intListToString(self.knap.encrypt(phrase, self.peerKey))
        self.send_msg(self.peerSocket, formatedPhrase)

        if self.type == 0:
            # Assembling the phrase
            phrase += self.knap.decrypt(functions.stringToIntList(self.read(self.peerSocket))).decode('utf-8')
        else:
            phrase = self.knap.decrypt(functions.stringToIntList(self.read(self.peerSocket))).decode('utf-8') + phrase
        
        print('Assembled the encrypting phrase with my peer')
        print(phrase)

        self.solitairePhrase = phrase

    def peerCommunication(self):
        msg = ''
        stop = False
        if self.type == 0:
            while stop == False:
                msg = input()
                if msg == 'exit':
                    stop = True
                # Encrypting the message
                encMsg = functions.intListToString(self.sol.encrypt(msg))
                # Sending the message with streamCount
                self.send_msg(self.peerSocket, str(self.sol.streamCount))
                self.send_msg(self.peerSocket, encMsg)

                # Reading stream count
                peerStreamCount = int(self.read(self.peerSocket).decode('utf-8'))
                # Reading message
                formatedMsg = functions.stringToIntList(self.read(self.peerSocket).decode('utf-8'))

                # Checking if streamCount is shifted
                functions.handleDesincronization(peerStreamCount, self.sol, len(formatedMsg))

                msg = self.sol.decrypt(formatedMsg)
                if msg == 'exit':
                    stop = True
                print(msg)

            self.send_msg(self.socket, json.dumps({"close": True}))
        else:
            while msg != 'exit':
                # Reading streamCount and msg
                peerStreamCount = int(self.read(self.peerSocket).decode('utf-8'))
                formatedMsg = functions.stringToIntList(self.read(self.peerSocket).decode('utf-8'))
                
                if formatedMsg == 'exit':
                    break

                # Checking if streamCount is shifted
                functions.handleDesincronization(peerStreamCount, self.sol, len(formatedMsg))

                print(self.sol.decrypt(formatedMsg))
                msg = input()
                encMsg = functions.intListToString(self.sol.encrypt(msg))
                self.send_msg(self.peerSocket, str(self.sol.streamCount))
                self.send_msg(self.peerSocket, encMsg)

            self.send_msg(self.socket, json.dumps({"close": True}))



print("Enter client type:")
print("0 - Conversation starter")
print("1 - Conversation accepter")

tp = int(input())
while int(tp) > 1:
    print("Incorrect input: type must be 0 or 1")
    tp = input()

client = Client(tp)


print('Select a phrase for encryption:')
phrase = input()

client.assemblePhrase(phrase)

client.initSolitaire()

client.peerCommunication()
