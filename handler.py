import base64
import inspect

from logger import *
from user import User
from channel import Channel
from commands import on_command

# TODO: CTCP responses
# TODO: on nick function

HANDLERS = {}


def raw(*cmds):
    def _decorate(func):
        for cmd in cmds:
            HANDLERS.setdefault(cmd.upper(), []).append(func)
        return func
    return _decorate


def handler(connection, prefix, command, args):
    data = {
        "connection": connection,
        "prefix": prefix,
        "command": command,
        "args": args,
    }
    for func in HANDLERS.get(command, []):
        _internal_launch(func, data)


def _internal_launch(func, data):
    sig = inspect.signature(func)
    params = []
    for arg in sig.parameters.keys():
        assert arg in data
        params.append(data[arg])
    func(*params)


@raw("PING")
def onping(connection, args):
    connection.write("PONG :" + " ".join(args))


@raw("AUTHENTICATE")
def sendauth(connection):
    auth_string = (connection.nick + "\00" + connection.nsuser + "\00"
                   + connection.nspass).encode()

    connection.write("AUTHENTICATE {}".format(
        base64.b64encode(auth_string).decode())
    )


@raw("CAP")
def handlecap(connection, args):
    command = args[1]
    if command == "LS":
        caplist = args[-1].split()
        caps = connection.caps.intersection(caplist)
        if len(caps) == 0:
            connection.write("CAP END")

        else:
            for cap in caps:
                connection.write("CAP REQ :{}".format(cap))
                capincrement(connection)

    elif command == "ACK":
        cap = args[2]
        if cap == "sasl":
            connection.cansasl = True
            capincrement(connection)
            connection.write("AUTHENTICATE PLAIN")
        elif cap == "userhost-in-names":
            connection.uhnames = True

        capdecrement(connection)

    elif command == "NAK":
        cap = args[2]
        capdecrement(connection)
        if cap == "userhost-in-names":
            connection.uhnames = False
        elif cap == "sasl":
            connection.cansasl = False


def capincrement(connection):
    connection.capcount += 1


@raw("903", "904")
def capdecrement(connection):
    connection.capcount -= 1
    if connection.capcount <= 0:
        connection.write("CAP END")


@raw("376")
def onendmotd(connection):
    if not connection.cansasl:
        identify(connection)
    for command in connection.commands:
        connection.write(command)
    connection.join(connection.adminchan)
    connection.join(connection.joinchannels)


def identify(connection):
    connection.write("PRIVMSG NickServ :IDENTIFY {nsnick} {nspass}".format(
        nsnick=connection.nsuser, nspass=connection.nspass
    ))


@raw("PRIVMSG")
def onprivmsg(connection, args, prefix):
    if args[1].startswith(connection.cmdprefix):
        on_command(connection, args, prefix)


# :Cloud-9.A_DNet.net 353 Roy_Mustang = #adtest :@Roy_Mustang
# :Cloud-9.A_DNet.net 366 Roy_Mustang #adtest :End of /NAMES list.


@raw("353")
def onnames(connection, args):
    names = args[3].split()
    chan: Channel = connection.channels[args[2]]

    # clear out the current user list
    if not chan.receivingnames:
        chan.receivingnames = True
        for user in chan.users:
            usero: User = chan.users[user].user
            del usero.channels[chan.name]
        chan.users = {}

    for mask in names:
        mask = mask.strip()
        if mask[0] in ["!", "@", "%", "+"]:
            prefix = mask[0]
            mask = mask[1:]
            if prefix == "!":
                admin = True
            elif prefix == "@":
                op = True
            elif prefix == "%":
                hop = True
            elif prefix == "+":
                voice = True
        admin, op, hop, voice = False, False, False, False
        temp = User.add(connection, mask)

        chan.adduser(connection, temp, isop=op, ishop=hop,
                     isvoice=voice, isadmin=admin)


@raw("366")
def onnamesend(connection, args):
    chan = connection.channels[args[1]]
    chan.receivingnames = False
    logchan(chan)


@raw("JOIN")
def onjoin(connection, prefix, args):
    chan = connection.channels.get(args[0])
    nick = prefix.split("!")[0]
    user = connection.users.get(nick)
    name = args[0]
    if not chan:
        connection.channels[name] = Channel(name, connection)

    if not user:
        User.add(connection, prefix)

    if not connection.channels[name].users.get(nick):
        chan = connection.channels[name]
        user = connection.users[nick]
        chan.adduser(connection, user)
    logall(connection)


@raw("005")
def onisupport(connection, args):
    tokens = args[1:-1]
    for token in tokens:
        if "NETWORK" in token:
            connection.networkname = token.split("=")[1]

        elif "PREFIX" in token:
            pfx = token.split("=")[1]
            pfx, modes = pfx.split(")", 1)
            pfx = pfx[1:]
            connection.Pmoded = dict(zip(pfx, modes))
            connection.Pmodes.update(pfx)

        elif "CHANMODES" in token:
            modes = token.split("=")[1]
            A, B, C, D = modes.split(",")
            connection.Amodes.update(A)
            connection.Bmodes.update(B)
            connection.Cmodes.update(C)
            connection.Dmodes.update(D)

        elif "EXCEPTS" in token:
            mode = token.split("=")[1]
            connection.Amodes.add(mode)
            connection.banexept.add(mode)

        elif "INVEX" in token:
            mode = token.split("=")[1]
            connection.Amodes.add(mode)
            connection.invex.add(mode)


@raw("MODE")
def onmode(connection, args):
    target = args[0]
    modes = args[1]
    modeargs = args[2:]
    adding = True
    count = 0
    if target == connection.nick:
        return
    chan = connection.channels[target]
    for mode in modes:
        if mode == "+":
            adding = True
            continue
        elif mode == "-":
            adding = False
            continue
        elif mode in connection.Amodes:
            count += 1
        elif mode in connection.Bmodes:
            count += 1
        elif mode in connection.Cmodes:
            if adding:
                count += 1
        elif mode in connection.Dmodes:
            pass
        elif mode in connection.Pmodes:
            nick = modeargs[count]
            log(str(("+" if adding else "-") + mode + " " + nick))
            membership = chan.users[nick]

            if mode == "o":
                membership.isop = adding
            elif mode == "h":
                membership.ishop = adding
            elif mode == "v":
                membership.isvoice = adding
            elif mode == "Y":
                membership.isadmin = adding
            count += 1
            logchan(chan)

# TODO: Deal with parts/kicks for myself


@raw("PART")
def onpart(connection, prefix, args):
    chan: Channel = connection.channels.get(args[0], None)
    user: User = connection.users.get(prefix.split("!")[0], None)
    if not chan:
        log("WTF? I just got a part for a channel I dont have, "
            "channel was {c}".format(c=args))
        logall(connection)

    if user.nick == connection.nick:
        chan.cleanup()
        log(connection.channels)
    else:
        chan.deluser(connection, user)
    logall(connection)


@raw("KICK")
def onkick(connection, args):
    user = connection.users.get(args[1], None)
    chan = connection.channels.get((args[0]), None)
    if user and chan:
        chan.deluser(connection, user)
    logall(connection)

