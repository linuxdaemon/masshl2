import socket
import ssl
import sys
import select
from logger import log
from handler import handler


class Connection:
    def __init__(self, port, host, isssl, nsuser, nspass, nick, user,
                 gecos="A_D's anti mass highlight bot"):
        self.port = port
        self.host = host
        self.ssl = isssl
        self.socket = socket.socket()
        self.buffer = b""
        self.uhnames = False
        self.nick = nick
        self.user = user
        self.gecos = gecos
        self.nsuser = nsuser
        self.nspass = nspass
        self.channels = {}
        self.users = {}

    def connect(self):
        if self.ssl:
            self.socket = ssl.wrap_socket(self.socket)
        self.socket.connect((self.host, self.port))
        self.write("CAP LS")
        self.write("NICK {nick}".format(nick=self.nick))
        self.write("USER {user} * * :{gecos}".format(user=self.user, gecos=self.gecos))

    def read(self):
        readable, _, _ = select.select([self.socket], [], [], 5)
        if self.socket in readable:
            data = self.socket.recv(65535)
            if not data:
                self.socket.close()
                # TODO: Get the full dead parrot rant
                sys.exit("Socket Closed. This socket is no more, it has ceased to be. "
                         "Its expired and gone to meet its maker. THIS IS AN EX SOCKET!")
            self.parse(data)

    def write(self, data):
        if isinstance(data, bytes):
            self.socket.send(data + b"\r\n")
            log(data.decode(), "ircout")
        else:
            self.socket.send((data + "\r\n").encode())
            log(data, "ircout")

    def parse(self, data):
        self.buffer += data
        while b"\r\n" in self.buffer:
            raw, self.buffer = self.buffer.split(b"\r\n", 1)
            line = raw.decode()
            log(line, "ircin")
            if line[0] == ":":
                prefix, line = line.split(None, 1)
                prefix = prefix[1:]
            else:
                prefix = None

            args = line.split(" ")
            cmd = args.pop(0)
            i = 0
            while i < len(args):
                if args[i][0] == ":":
                    args[i] = " ".join(args[i:])[1:]
                    del args[i + 1:]
                i += 1
            handler(self, prefix, cmd, args)