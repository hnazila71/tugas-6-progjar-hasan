import sys
import os
import json
import uuid
import logging
from queue import  Queue

class Chat:
	def __init__(self):
		self.groups={}
		self.sessions={}
		self.users = {}
		self.users['messi']={ 'nama': 'Lionel Messi', 'negara': 'Argentina', 'password': 'surabaya', 'incoming' : {}, 'outgoing': {}}
		self.users['henderson']={ 'nama': 'Jordan Henderson', 'negara': 'Inggris', 'password': 'surabaya', 'incoming': {}, 'outgoing': {}}
		self.users['lineker']={ 'nama': 'Gary Lineker', 'negara': 'Inggris', 'password': 'surabaya','incoming': {}, 'outgoing':{}}
	
	def write_incoming(self, data):
		j=data.split(" ")
		try:
			usernamefrom = j[1].strip()
			usernameto = j[2].strip()
			message = ""
			for w in j[3:]:
				message="{} {}".format(message, w)
			s_to = self.get_user(usernameto)
			if (s_to==False):
				return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
			message = { 'msg_from': usernamefrom, 'msg_to': s_to['nama'], 'msg': message }
			inqueue_receiver= s_to['incoming']
			try:
				inqueue_receiver[usernamefrom].put(message)
			except KeyError:
				inqueue_receiver[usernamefrom]=Queue()
				inqueue_receiver[usernamefrom].put(message)
			return {'status': 'OK', 'message': 'Message Sent', 'sendback': message}
		except IndexError:
			return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}
	
	def write_outgoing(self, data):
		usernamefrom = data['msg_from']
		outqueue_sender = self.get_user(usernamefrom)
		try:	
			outqueue_sender[usernamefrom].put(data)
		except KeyError:
			outqueue_sender[usernamefrom]=Queue()
			outqueue_sender[usernamefrom].put(data)
	
	def groupOtherServer(self, socket, data):
		j=data.split(" ")
		username = j[1]
		groupname = j[2]
		state = j[3]
		hasil = self.group_chat(username, groupname, state, socket)
		return hasil
	
	def broadcast(self, groupname, data):
		for c in self.groups[groupname]:          
			c[1].sendall(data.encode())

	def exitGroup(self, groupname, client):
		self.groups[groupname].remove(client)

	def proses(self, data, socket=[]):
		j=data.split(" ")
		try:
			command=j[0].strip()
			if (command=='auth'):
				username=j[1].strip()
				password=j[2].strip()
				logging.warning("AUTH: auth {} {}" . format(username,password))
				return self.autentikasi_user(username,password)
			elif (command=='send'):
				sessionid = j[1].strip()
				usernameto = j[2].strip()
				message=""
				for w in j[3:]:
					message="{} {}" . format(message,w)
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom,usernameto))
				return self.send_message(sessionid,usernamefrom,usernameto,message)
			elif (command=='inbox'):
				sessionid = j[1].strip()
				username = self.sessions[sessionid]['username']
				logging.warning("INBOX: {}" . format(sessionid))
				return self.get_inbox(username)
			elif (command=='group'):
				sessionid = j[1]
				groupname = j[2]
				state = j[3]
				logging.warning("GROUP: {}".format(groupname))
				username = self.sessions[sessionid]['username']
				if username:
					return self.group_chat(username, groupname, state, socket)
				else:
					return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
			else:
				return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
		except KeyError:
			return { 'status': 'ERROR', 'message' : 'Informasi tidak ditemukan'}
		except IndexError:
			return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}

	def autentikasi_user(self,username,password):
		if (username not in self.users):
			return { 'status': 'ERROR', 'message': 'User Tidak Ada' }
		if (self.users[username]['password']!= password):
			return { 'status': 'ERROR', 'message': 'Password Salah' }
		tokenid = str(uuid.uuid4()) 
		self.sessions[tokenid]={ 'username': username, 'userdetail':self.users[username]}
		return { 'status': 'OK', 'tokenid': tokenid }

	def get_user(self,username):
		if (username not in self.users):
			return False
		return self.users[username]

	def send_message(self,sessionid,username_from,username_dest,message):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		s_to = self.get_user(username_dest)
		
		if (s_fr==False or s_to==False):
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

		message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
		outqueue_sender = s_fr['outgoing']
		inqueue_receiver = s_to['incoming']
		try:	
			outqueue_sender[username_from].put(message)
		except KeyError:
			outqueue_sender[username_from]=Queue()
			outqueue_sender[username_from].put(message)
		try:
			inqueue_receiver[username_from].put(message)
		except KeyError:
			inqueue_receiver[username_from]=Queue()
			inqueue_receiver[username_from].put(message)
		return {'status': 'OK', 'message': 'Message Sent'}

	def get_inbox(self,username):
		s_fr = self.get_user(username)
		incoming = s_fr['incoming']
		msgs={}
		for users in incoming:
			msgs[users]=[]
			while not incoming[users].empty():
				msgs[users].append(s_fr['incoming'][users].get_nowait())
		return {'status': 'OK', 'messages': msgs}
	
	def group_chat(self, username, groupname, state, socket):
		groups = self.groups
		client = [username, socket]
		if groupname not in groups and state != 'comeback':
			return {'status': 'PENDING', 'message': f'Tidak ada grup {groupname} di server'}
		elif state == 'comeback':
			groups[groupname] = [client]
		else:
			groups[groupname].append(client)

		sambutan = f"{username} telah bergabung"
		self.broadcast(groupname, sambutan)
		while True:
			try:
				chat = socket.recv(1024).decode()
				print(f"menerima pesan dari client = {chat}")
				if chat != 'exit':
					chat = f"{username}: {chat}"
					self.broadcast(groupname, chat)
				else:
					socket.send("exit".encode())
					self.exitGroup(groupname, client)
					print(f'user {username} telah keluar')
					self.broadcast(groupname, f"{username} meninggalkan group")
					break
			except:
				self.exitGroup(groupname, client)
				break
		if len(groups[groupname]) == 0:
			groups.pop(groupname)
		return {'status': 'OK', 'message': f'Telah keluar dari grup {groupname}'}


if __name__=="__main__":
	j = Chat()
	sesi = j.proses("auth messi surabaya")
	print(sesi)
	tokenid = sesi['tokenid']
	print(j.proses("send {} henderson hello gimana kabarnya son " . format(tokenid)))
	print(j.proses("send {} messi hello gimana kabarnya mess " . format(tokenid)))

	print("isi mailbox dari messi")
	print(j.get_inbox('messi'))
	print("isi mailbox dari henderson")
	print(j.get_inbox('henderson'))