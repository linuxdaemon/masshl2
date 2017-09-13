import inspect
from handler import message
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from parser import Message
# from logger import *

# TODO: for masshl, channel notice checking too

COMMANDS = {}


def command(*cmds):
    def _decorate(func):
        for cmd in cmds:
            assert cmd not in COMMANDS
            COMMANDS[cmd] = func
        return func

    return _decorate


# @command("print")
# def printlog(connection):
#     logcentered("MODES", connection=connection)
#     log("A: " + str(connection.a_modes))
#     log("B: " + str(connection.b_modes))
#     log("C: " + str(connection.c_modes))
#     log("D: " + str(connection.d_modes))
#     log("P: " + str(connection.p_modes))
#
#
# @command("die")
# def die(connection):
#     connection.quit("Controller requested disconnect")
#
#
# @command("nickl")
# def nickl(connection, channel):
#     logcentered("nicks", connection=connection)
#     for nick in channel.memberships.keys():
#         print(nick)
#
#
# @command("stop")
# def stop(connection):
#     connection.bot.stop("Controller requested disconnect")
#
#
# @command("join")
# def join(connection, cmdargs):
#     connection.join(cmdargs)
#
#
# @command("part")
# def part(connection, cmdargs):
#     connection.part(cmdargs)
#
# 
# @command("raw")
# def raw(connection, cmdargs):
#     if cmdargs:
#         connection.write(cmdargs)

@message
def on_msg(msg: 'Message'):
    if not msg.message.startswith(msg.conn.cmdprefix):
        return

    cmd = msg.s_msg[0][1:]

    if len(msg) > 1:
        args = msg.s_msg[1:]
    else:
        args = []

    handler = COMMANDS.get(cmd)
    if handler and callable(handler):
        sig = inspect.signature(handler)
        data = {
            "msg": msg,
            "cmd": cmd,
            "args": args
        }
        # send it the requested args
        return handler(*[data[arg] for arg in sig.parameters.keys()])


@command("msgme")
def msgme(msg: 'Message', args):
    msg.origin.send_message("requested")


@command("reload")
def reload(msg: 'Message', args):
    if len(args) < 1:
        msg.target.send_message("reload requires an argument")
        return

    def todo():
        for plugin_name in args:
            resp = msg.bot.load_plugin(plugin_name)
            if resp:
                msg.target.send_message(str(resp))

    return todo


@command("say")
def say(args):
    return " ".join(args)


@command("print")
def cmd_print(msg):
    return str(msg.bot.message_hooks)

# def on_command(connection, args, prefix):
#     temp = args[1][1:].split(None, 1)
#     cmd = temp.pop(0)
#     cmdargs = ""
#     if temp:
#         cmdargs = temp.pop(0)
#
#     handler = COMMANDS.get(cmd)
#     if handler and callable(handler):
#         sig = inspect.signature(handler)
#         channel = connection.channels.get(args[0])
#         data = {
#             "connection": connection,
#             "channel": channel,
#             "cmdargs": cmdargs,
#         }
#         args = [data[arg] for arg in sig.parameters.keys()]
#         handler(*args)
