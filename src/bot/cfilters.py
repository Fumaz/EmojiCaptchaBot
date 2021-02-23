import re
from re import Pattern
from typing import Union

from pyrogram import filters

from util import config


def group_command(commands: Union[str, list], prefixes: Union[str, list] = "/"):
    if not isinstance(commands, list):
        commands = [commands]

    for command in list(commands):
        commands.append(f'{command}@{config.BOT_USERNAME}')

    return filters.group & filters.command(commands, prefixes)


def service(name: str):
    return filters.create(lambda _, __, m: m.service and getattr(m, name, None) is not None)


def action_regex(pattern: Union[Pattern, str], flags: int = 0):
    def func(flt, _, update):
        user = update.db_user

        if not user:
            return False

        update.action_matches = list(flt.p.finditer(user.action)) or None

        return bool(update.action_matches)

    return filters.create(
        func,
        "ActionRegexFilter",
        p=pattern if isinstance(pattern, Pattern) else re.compile(pattern, flags)
    )


bot_admin = filters.create(lambda _, __, u: u.db_user.is_admin)
chat_admin = filters.create(lambda _, __, u: u.db_user and u.db_user.id in u.db_chat.administrators)
has_permissions = filters.create(lambda _, __, u: u.db_chat.has_permissions)
self_was_added = filters.create(lambda _, __, m: m.self_was_added)
