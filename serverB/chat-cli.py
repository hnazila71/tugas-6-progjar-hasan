import socket
import os
import json
from threading import Thread

TARGET_IP = "127.0.0.1"
TARGET_PORT = 5002

class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP,TARGET_PORT)
        self.sock.connect(self.server_address)
        self.tokenid=""

    def sendstring(self,string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                print("diterima dari server",data)
                if (data):
                    receivemsg = "{}{}" . format(receivemsg,data.decode())  #data harus didecode agar dapat di operasikan dalam bentuk string
                    if receivemsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return { 'status' : 'ERROR', 'message' : 'Gagal'}

    def client_received(self):
        while True:
            message = self.sock.recv(1024).decode()
            if message != 'exit':
                print(message)
            else:
                break

    def client_send(self):
        while True:
            chat = input("")
            self.sock.sendall(chat.encode())
            if chat=='exit':
                break

    def proses(self,cmdline):
        j=cmdline.split(" ")
        try:
            command=j[0].strip()
            if (command=='auth'):
                username=j[1].strip()
                password=j[2].strip()
                return self.login(username,password)
            elif (command=='send'):
                usernameto = j[1].strip()
                message=""
                for w in j[2:]:
                   message="{} {}" . format(message,w)
                return self.sendmessage(usernameto,message)
            elif (command=='inbox'):
                return self.inbox()
            elif (command=='group'):
                return self.groupChat(j[1])
            else:
                return "*Maaf, command tidak benar"
        except IndexError:
                return "-Maaf, command tidak benar"

    def login(self,username,password):
        string="auth {} {} \r\n" . format(username,password)
        result = self.sendstring(string)
        if result['status']=='OK':
            self.tokenid=result['tokenid']
            return "username {} logged in, token {} " .format(username,self.tokenid)
        else:
            return "Error, {}" . format(result['message'])

    def sendmessage(self,usernameto="xxx",message="xxx"):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="send {} {} {} \r\n" . format(self.tokenid,usernameto,message)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "message sent to {}" . format(usernameto)
        else:
            return "Error, {}" . format(result['message'])
    def inbox(self):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="inbox {} \r\n" . format(self.tokenid)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "{}" . format(json.dumps(result['messages']))
        else:
            return "Error, {}" . format(result['message'])

    def groupChat(self, namagrup):
        if (self.tokenid==""):
            return "Error, not authorized"
        string='group {} {} origin \r\n'.format(self.tokenid, namagrup)
        self.sock.sendall(string.encode())

        receiveThread = Thread(target=self.client_received, args=())
        sendThread = Thread(target=self.client_send, args=())
        receiveThread.start()
        sendThread.start()
        receiveThread.join()
        sendThread.join()

        try:
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                print("diterima dari server",data)
                if (data):
                    receivemsg = "{}{}" . format(receivemsg,data.decode())
                    if receivemsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        receivemsg = json.loads(receivemsg)
                        break
        except:
            self.sock.close()
            receivemsg = { 'status' : 'ERROR', 'message' : 'Gagal'}
        
        if receivemsg['status']=='OK':
            return "{}".format(receivemsg['message'])
        else:
            return "Error, {}".format(receivemsg['message'])


if __name__=="__main__":
    cc = ChatClient()
    while True:
        cmdline = input("Command {}:" . format(cc.tokenid))
        print(cc.proses(cmdline))
