from pyrogram import Client

from bot import cfilters
from db.models import *

PRE_HANDLER = -3
MIGRATION = -2
WELCOME = -1


@Client.on_message(group=PRE_HANDLER)
async def on_message(client, message):
    message.self_was_added = False

    message.db_user = await User.from_pyrogram(message)
    message.db_chat = await Chat.from_pyrogram(message)

    if message.db_chat and message.db_chat.is_first_use:
        await message.db_chat.reload(client, update_date=False)

        if message.db_user:
            message.db_chat.set_language(message.db_user.language)

    if message.new_chat_members:
        message.db_new_chat_members = []

        for user in message.new_chat_members:
            if user.is_self:
                message.self_was_added = True
                continue

            message.db_new_chat_members.append(await User.from_pyrogram(user))


@Client.on_callback_query(group=PRE_HANDLER)
async def on_callback_query(_, callback):
    callback.db_user = await User.from_pyrogram(callback)
    callback.db_chat = await Chat.from_pyrogram(callback)


@Client.on_message(cfilters.service('migrate_from_chat_id'), group=MIGRATION)
async def on_migration(client, message):
    message.db_chat = message.db_chat.migrate(message.migrate_from_chat_id, client)


@Client.on_message(group=WELCOME)
async def on_welcome(_, message):
    if message.db_chat and message.db_chat.type != ChatType.CHANNEL \
            and (message.db_chat.is_first_use or message.self_was_added):
        with db_session:
            db_chat = message.db_chat.current

            await message.reply_text(db_chat.get_message('added_to_group'))
