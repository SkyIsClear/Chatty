# server for the ChattY chat
# made by Yedaya Katsman 26/07/2018
# for a school project summer of 2018
import socket, select, errno
import json
import sqlite3
import sys
import smtplib
from email.mime.text import MIMEText
from random import randint
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode


class SQL:
    # class that controls all communications between the server and the sql database

    def __init__(self):
        # connects to database
        self.Connection = sqlite3.connect('ChattyQuery.db')
        self.cursor = self.Connection.cursor()
        try:
            # creqating sql table for all users
            self.cursor.execute('''CREATE TABLE users
                                   (username TEXT PRIMARY KEY, email TEXT, firstName TEXT,
                                    lastName TEXT, birthDate TEXT, password TEXT, image INTEGER, code INTEGER)''')
        except Exception as error:
            print error, "line: %d" % sys.exc_info()[-1].tb_lineno
            pass

    def InsertNewUser(self, regInfo):
        # function to create a new user in the sy
        print "inserting new user..."
        self.cursor.execute(
            '''INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', regInfo)
        self.Connection.commit()

    def Select(self, command, args):
        self.cursor.execute(command, args)
        results = self.cursor.fetchone()
        if results:
            return results[0]
        return None

    def Update(self, command, args):
        self.cursor.execute(command, args)


class Server(object):
    def __init__(self):
        self.running = True

        self.Rooms = [[], [], [], []]

        self.DataBase = SQL()
        try:
            self.serverSocket = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
            self.serverSocket.bind(('0.0.0.0', 35628))
            self.serverSocket.listen(50)
            print "connected"
        except Exception as error:
            # print error, "line: %d" % sys.exc_info()[-1].tb_lineno
            print "couldn't connect"

    def loop(self):
        self.ConnectedClients = {}  # list of dictionaries that containes usernames and their respective socket objects
        self.MessagesToSend = []
        self.CloseList = []
        try:
            while self.running:
                rlist, wlist, xlist = select.select(
                    [self.serverSocket] + [user.socket for user in
                                           Users.UsersList],
                    [user.socket for user in Users.UsersList], []
                )
                if rlist:
                    for CurrentSocket in rlist:
                        if CurrentSocket is self.serverSocket:
                            (newSocket, address) = self.serverSocket.accept()
                            newUser = Users(newSocket)
                            try:
                                # four way handshake of exchanging encryption keys
                                newUser.socket.send(
                                    newUser.privateKey.publickey().exportKey())
                                newUser.ClientPublicKey = RSA.import_key(
                                    newUser.socket.recv(271))
                                cipherRsa = PKCS1_OAEP.new(
                                    newUser.ClientPublicKey)
                                # print 'IV length: %s' % len(newUser.InitializationVector)
                                encAESKey = cipherRsa.encrypt(json.dumps(
                                    {'SKey': b64encode(newUser.SessionKey),
                                     'IV': b64encode(
                                         newUser.InitializationVector)}))
                                newUser.socket.send(encAESKey)
                                ClientRSACipher = PKCS1_OAEP.new(
                                    newUser.privateKey)
                                ClientAESKey = json.loads(
                                    ClientRSACipher.decrypt(
                                        newUser.socket.recv(128)))
                                # print 'client aes key: %s' % ClientAESKey
                                newUser.ClientSessionKey = b64decode(
                                    ClientAESKey['SKey'])
                                newUser.ClientInitializationVector = b64decode(
                                    ClientAESKey['IV'])
                            except Exception as error:
                                Users.UsersList.remove(newUser)
                        else:
                            try:
                                receivedMessage = CurrentSocket.recv(8192)
                                messages = receivedMessage.split('|')[:-1]
                            except Exception as error:
                                # deleting socket from dictionary by finding index of it and finding key which corresponds to it
                                Users.RemoveBySocket(CurrentSocket)
                                break
                            if receivedMessage == "":
                                Users.RemoveBySocket(CurrentSocket)
                                CurrentSocket.close()
                            else:
                                for message in messages:
                                    user = Users.GetBySocket(CurrentSocket)
                                    # print "IV: %s" % user.ClientInitializationVector
                                    # print 'IV length: %s' % len(user.ClientInitializationVector)
                                    AESCipher = AES.new(user.ClientSessionKey,
                                                        AES.MODE_CBC,
                                                        user.ClientInitializationVector)
                                    plainText = json.loads(str(
                                        AESCipher.decrypt(
                                            b64decode(message))).strip('$'))
                                    # print 'plain text: %s' % plainText
                                    user.ClientSessionKey = b64decode(
                                        plainText['newKey'])
                                    user.ClientInitializationVector = b64decode(
                                        plainText['newIV'])
                                    self.ProcessMessage(plainText['message'],
                                                        Users.GetBySocket(
                                                            CurrentSocket))
                if wlist and self.MessagesToSend:
                    for message in self.MessagesToSend:
                        if not message[1] in Users.UsersList:
                            self.MessagesToSend.remove(message)
                        elif message[
                            1].socket in wlist:  # checking if any of the messages are for user who can accept them
                            encodedMsg = json.dumps(message[0],
                                                    separators=(',',
                                                                ':'))  # encoding dictionary to text for delivery
                            try:
                                print 'encrypting message: %s' % encodedMsg
                                cipherText = self.encryptMessage(encodedMsg,
                                                                 message[
                                                                     1]) + '|'
                                message[1].socket.send(cipherText)
                                # print 'sent message: %s to %s' % (cipherText, message[1])
                            except socket.error:
                                Users.UsersList.remove(message[1])
                                # del self.ConnectedClients[message[1]]
                            self.MessagesToSend.remove((message))
                if self.CloseList:
                    for client in self.CloseList:
                        client.socket.close()
                        self.Rooms[client.room].remove(client)
                        Users.UsersList.remove(client)
        except Exception as error:
            pass
            print error, " line: %d" % sys.exc_info()[-1].tb_lineno
        finally:
            print "server closed"
            self.serverSocket.close()

    def ProcessMessage(self, message, sender):
        message = json.loads(message)

        action = message["opcode"]  # getting action requested by clien
        if action == "register":
            if self.DataBase.Select('SELECT username FROM users WHERE email=?',
                                    (message['email'],)):
                self.MessagesToSend.append((
                    {'opcode': 'regConfirm', 'success': 0,
                     'error': "email is already in use"}, sender))
                return
            if self.DataBase.Select('SELECT email FROM users WHERE username=?',
                                    (message['username'],)):
                self.MessagesToSend.append((
                    {'opcode': 'regConfirm', 'success': 0,
                     'error': "username already exists in system"}, sender))
                return
            self.DataBase.InsertNewUser((message['username'], message['email'],
                                         message['firstName'],
                                         message['lastName'],
                                         message['birthDate'],
                                         message['password'],
                                         message['image'], 0,))
            self.MessagesToSend.append(
                ({'opcode': 'regConfirm', 'success': 1, 'error': ""}, sender))
            sender.SetName(message['username'])

        if action == 'login':
            # checking if password matches the database
            hash = self.DataBase.Select(
                '''SELECT password FROM users WHERE username=?''',
                (message['username'],))
            if not hash or hash != message['password']:
                self.MessagesToSend.append((
                    {'opcode': 'loginConfirm', 'success': 0,
                     'error': 'Username or password are incorrect'}
                    , sender))
            elif hash == message['password']:
                if sender.SetName(message['username']):
                    # checks if user is not logged in already
                    self.MessagesToSend.append(({'opcode': 'loginConfirm',
                                                 'success': 1, 'error': ''},
                                                sender))
                else:
                    print "double login"
                    self.MessagesToSend.append(
                        ({'opcode': 'loginConfirm', 'success': 0,
                          'error': 'You are already logged in on another device'},
                         sender))
        if action == 'logout':
            self.CloseList.append(sender)
            if sender.room:
                for user in self.Rooms[sender.room]:
                    self.MessagesToSend.append(({'opcode': 'userLeft',
                                                 'username': sender.username},
                                                user))
            Users.RemoveByName(message['username'])

        if action == 'joinRoom':
            if message['roomID'] <= 3 and message['roomID'] >= 0:
                self.Rooms[message['roomID']].append(sender)
                sender.room = message['roomID']
                self.MessagesToSend.append((
                    {'opcode': 'roomConfirm', 'success': 1, 'error': ""}
                    , sender))
                for user in self.Rooms[message['roomID']]:
                    self.MessagesToSend.append((
                        {'opcode': 'userJoin', 'username': sender.username,
                         'image': ''}, user))
            else:
                self.MessagesToSend.append(
                    ({'opcode': 'roomConfirm', 'success': 0,
                      'error': "room does not exist"}, sender))

        if action == 'message':
            print "Rooms: %s" % self.Rooms
            for client in self.Rooms[message['room']]:
                self.MessagesToSend.append(
                    ({'opcode': 'messageToYou', 'message': message['message'],
                      'sender': sender.username}, client))

        if action == 'forgotPassword':
            code = randint(100000, 999999)
            email = self.DataBase.Select(
                '''SELECT email FROM users WHERE username = ?''',
                (message['username'],))
            if email == message['email']:

                fromx = 'serverchatty@gmail.com'
                to = email
                msg = MIMEText('Your one time code is %s' % code)
                msg['Subject'] = 'Chatty Password reset'
                msg['From'] = fromx
                msg['To'] = to

                try:
                    server = smtplib.SMTP('smtp.gmail.com:587')
                    server.starttls()
                    server.ehlo()
                    server.login('serverchatty@gmail.com', 'super secret')
                    server.sendmail(fromx, to, msg.as_string())
                    server.quit()

                    print 'Email sent!'
                    self.MessagesToSend.append(({'opcode': 'codeConfirm',
                                                 'success': 1, 'error': ''},
                                                sender))
                except:
                    print 'Something went wrong...'
                    self.MessagesToSend.append(
                        ({'opcode': 'codeConfirm', 'success': 0,
                          'error': 'email doesn\'t exist'}, sender))
        if action == 'resetPassword':
            self.DataBase.Update(
                '''UPDATE users SET password = ? WHERE username = ?''',
                (message['newPassword'], sender.username))
            self.MessagesToSend.append(
                ({'opcode': 'resetConfirm', 'success': 1}, sender))

    def encryptMessage(self, message, target):
        OldAESCipher = AES.new(target.SessionKey, AES.MODE_CBC,
                               target.InitializationVector)
        target.GenerateNewKey()
        plainText = json.dumps(
            {'newKey': b64encode(target.SessionKey),
             'newIV': b64encode(target.InitializationVector),
             'message': message})
        # print 'plain text: %s' % plainText
        rlen = 16 - (len(plainText) % 16)
        plainText = plainText + '$' * rlen
        # print 'padded plain text: %s' % plainText
        cipherText = b64encode(OldAESCipher.encrypt(plainText))
        return cipherText


class Users(object):
    # users class. each instance is a separate user that has username, socket, id etc.
    #   the class keeps track of all users and has static methods to find certain users
    #     or delete them

    UsersList = []

    @staticmethod
    def GetByName(username):
        for user in Users.UsersList:
            if user.username == username:
                return user
        return None

    @staticmethod
    def GetBySocket(socket):
        for user in Users.UsersList:
            if user.socket == socket:
                return user
        return None

    @staticmethod
    def GetByID(id):
        for user in Users.UsersList:
            if user.id == id:
                return user
        return None

    @staticmethod
    def RemoveByID(id):
        for user in Users.UsersList:
            if user.id == id:
                Users.UsersList.remove(user)

    @staticmethod
    def RemoveByName(username):
        for user in Users.UsersList:
            if user.username == username:
                Users.UsersList.remove(user)

    @staticmethod
    def RemoveBySocket(socket):
        for user in Users.UsersList:
            if user.socket is socket:
                Users.UsersList.remove(user)

    def __init__(self, socket, username=''):
        self.socket = socket
        self.username = username
        self.id = len(type(self).UsersList) + 1
        self.room = None

        type(self).UsersList.append(self)

        self.privateKey = RSA.generate(1024)
        self.ClientPublicKey = None
        self.SessionKey = get_random_bytes(16)
        self.InitializationVector = get_random_bytes(16)

        self.ClientSessionKey = None
        self.ClientInitializationVector = None

    def SetName(self, username):
        if type(self).GetByName(username):
            return False
        self.username = username
        return True

    def GenerateNewKey(self):
        self.SessionKey = get_random_bytes(16)
        self.InitializationVector = get_random_bytes(16)

    def __str__(self):
        return 'username: %s, id: %s,\n private key: |%s| \n client public key: |%s| \n session key: |%s| \n client initialization vector: |%s|' % (
            self.username, self.id, self.privateKey.exportKey(),
            self.ClientPublicKey.exportKey(), self.SessionKey,
            self.InitializationVector)


def main():
    server = Server()
    # setting up server
    server.loop()
    # starting the server infinite loop


if __name__ == "__main__":
    main()
