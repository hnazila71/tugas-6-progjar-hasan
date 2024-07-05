from socket import *
import socket
import threading
import time
import sys
import json
import logging
from chat import Chat

chatserver = Chat()
otherserver_address = ('0.0.0.0', 5001)

class ProcessTheClient(threading.Thread):
	def __init__(self, client_connection, client_address):
		self.client_connection = client_connection
		self.client_address = client_address
		threading.Thread.__init__(self)
	
	def make_otherserver_socket(self, server_address):
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			logging.warning(f"connecting to {server_address}")
			sock.connect(server_address)
			return sock
		except Exception as ee:
			logging.warning(f"error {str(ee)}")
	
	def sendToOtherServer(self, otherserver_connection, data):
		logging.warning('Isi data sebelum dikirim ke realm lain = {}'.format(data))
		otherserver_connection.sendall(data.encode())

		rcv = ""
		while True:
			data = otherserver_connection.recv(32)

			if data:
				d = data.decode()
				rcv += d
				if '\r\n\r\n' in rcv:
					msg = rcv.strip()
					msg = json.loads(msg)
					if msg['status'] == 'OK':
						sendback = msg.pop('sendback')
						chatserver.write_outgoing(sendback)
						rcv = json.dumps(msg)
						rcv += '\r\n\r\n'
						return rcv
					else:
						rcv = json.dumps(msg)
						rcv += '\r\n\r\n'
						return rcv
	
	def groupToOtherServer(self, otherserver_connection, client_connection, data):
		logging.warning('Isi data sebelum dikirim ke realm lain = {}'.format(data))
		j=data.split(" ")
		username = j[2]
		otherserver_connection.sendall(data.encode())
		rcv=""
		while True:
			data = otherserver_connection.recv(32)

			if data:
				d = data.decode()
				rcv += d
				if '\r\n\r\n' in rcv:
					print('data rcv yang diterima dari realm lain adalah', rcv)
					return rcv
				elif username in rcv:
					client_connection.sendall(rcv.encode())
					rcv=""
					send_from_otherserver = threading.Thread(target=self.client_send, args=(otherserver_connection, client_connection))
					received_from_otherserver = threading.Thread(target=self.otherserver_received, args=(otherserver_connection, client_connection))
					received_from_otherserver.start()
					send_from_otherserver.start()
					received_from_otherserver.join()
					send_from_otherserver.join()
	
	def otherserver_received(self, otherserver_socket, client_socket):
		while True:
			message = otherserver_socket.recv(1024).decode()
			client_socket.sendall(message.encode())
			if message == 'exit':
				break
    
	def client_send(self, otherserver_socket, client_socket):
		while True:
			message = client_socket.recv(1024).decode()
			otherserver_socket.sendall(message.encode())
			if message == 'exit':
				break

	def run(self):
		rcv=""
		kirim_balik = ''
		while True:
			data = self.client_connection.recv(32)
			if data:
				d = data.decode()
				rcv=rcv+d
				if rcv[-2:]=='\r\n':
					if 'server' in rcv:
						rcv = rcv.replace('server ', '')
						hasil = json.dumps(chatserver.write_incoming(rcv))
						hasil += '\r\n\r\n'
						logging.warning("balas ke  client: {}" . format(hasil))
						self.client_connection.sendall(hasil.encode())
						rcv=""
					
					elif 'check' in rcv:
						rcv = rcv.replace('check ', '')
						hasil = json.dumps(chatserver.groupOtherServer(self.client_connection, rcv))
						hasil += '\r\n\r\n'
						logging.warning("balas ke  client: {}" . format(hasil))
						self.client_connection.sendall(hasil.encode())
					
					else:
						logging.warning("data dari client: {}" . format(rcv))
						cekmsg = rcv.split(" ")
						command = cekmsg[0].strip()
						hasilchat = chatserver.proses(rcv, self.client_connection)
						if command == 'send' and hasilchat['status'] == 'ERROR':
							username = chatserver.sessions[cekmsg[1]]['username']
							if username:
								rcv = rcv.replace(cekmsg[1], username)
								pesan_ke_server_lain = 'server ' + rcv
								otherserver_connection = self.make_otherserver_socket(otherserver_address)
								hasil = self.sendToOtherServer(otherserver_connection, pesan_ke_server_lain)
								logging.warning("balas ke  client: {}" . format(hasil))
								self.client_connection.sendall(hasil.encode())
								rcv=""
							else:
								hasil = json.dumps(hasilchat)
								hasil=hasil+"\r\n\r\n"
								logging.warning("balas ke  client: {}" . format(hasil))
								self.client_connection.sendall(hasil.encode())
								rcv=""
						elif command=='group' and hasilchat['status'] == 'PENDING':
							username = chatserver.sessions[cekmsg[1]]['username']
							if username:
								rcv = rcv.replace(cekmsg[1], username)
								rcv = rcv.replace(cekmsg[3], 'other')
								cekmsg[3] = 'other'
								pesan_ke_server_lain = 'check ' + rcv
								otherserver_connection = self.make_otherserver_socket(otherserver_address)
								hasil = self.groupToOtherServer(otherserver_connection, self.client_connection, pesan_ke_server_lain)
								hasil = json.loads(hasil)
								if hasil['status'] == 'OK':
									hasil = json.dumps(hasil)
									hasil += '\r\n\r\n'
									self.client_connection.sendall(hasil.encode())
									rcv =""
								else:
									rcv = rcv.replace(username, cekmsg[1])
									rcv = rcv.replace(cekmsg[3], 'comeback')
									logging.warning(f"Tidak ada grup {cekmsg[2]} di realm lain, buat grup baru")
									hasil = chatserver.proses(rcv, self.client_connection)
									hasil = json.dumps(hasil)
									hasil = hasil + '\r\n\r\n'
									logging.warning("balas ke  client: {}" . format(hasil))
									self.client_connection.sendall(hasil.encode())
									rcv=""
							else:
								hasil = json.dumps(hasilchat)
								hasil=hasil+"\r\n\r\n"
								logging.warning("balas ke  client: {}" . format(hasil))
								self.client_connection.sendall(hasil.encode())
								rcv=""
						else:
							hasil = json.dumps(hasilchat)
							hasil=hasil+"\r\n\r\n"
							logging.warning("balas ke  client: {}" . format(hasil))
							self.client_connection.sendall(hasil.encode())
							rcv=""
			else:
				break
		self.connection.close()

class Server(threading.Thread):
	def __init__(self):
		self.the_clients = []
		self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		threading.Thread.__init__(self)

	def run(self):
		self.my_socket.bind(('0.0.0.0',5002))
		self.my_socket.listen(1)
		while True:
			self.connection, self.client_address = self.my_socket.accept()
			logging.warning("connection from {}" . format(self.client_address))
			clt = ProcessTheClient(self.connection, self.client_address)
			clt.start()
			self.the_clients.append(clt)
	

def main():
	svr = Server()
	svr.start()

if __name__=="__main__":
	main()