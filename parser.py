import re
import typing

if typing.TYPE_CHECKING:
    from user import User
    from channel import Channel
    from connection import Connection

PREFIX_RE = re.compile(r'(?P<nick>.+?)(?:!(?P<user>.+?))?(?:@(?P<host>.+?))?')


def parse_prefix(prefix):
    match = PREFIX_RE.fullmatch(prefix)
    return match.group('nick'), match.group('user'), match.group('host')


class Message:
    def __init__(self, connection, args, prefix, msg_type):
        self.conn: Connection = connection
        self.args = args
        self.prefix = prefix
        self.type = msg_type
        self.target: typing.Union[User, Channel]
        self.origin: typing.Union[User, None]
        self.message: str = ""
        self._parse_msg(prefix, args)
        self.s_msg = self.message.split(" ")
        self.eol_msg = []
        for i, word in enumerate(self.s_msg):
            self.eol_msg.append(self.s_msg[i:])

    @property
    def bot(self):
        return self.conn.bot

    def _parse_msg(self, prefix, args):
        nick, user, host = parse_prefix(prefix)
        if args[0][0] in self.conn.chantypes:
            self.target = self.conn.channels.get(args[0])
        else:
            self.target = self.conn.users.get(args[0])
        self.origin = self.conn.users.get(nick)
        if not self.origin and prefix != self.conn.server:
            self.conn.log.error("WTF? Got a message from someone I dont know")
        if not self.target:
            self.conn.log("WTF? Got a message pointed at nothing")
        self.message = args[1]

    def __str__(self):
        return self.prefix + " " + " ".join(self.args)

    def __len__(self):
        return len(self.s_msg)
