from pyrogram import Client, filters

from bot import cfilters
from localization import timeutils


@Client.on_message(cfilters.group_command(['reload', 'riavvia']) & cfilters.chat_admin)
async def on_reload(client, message):
    delay = message.db_chat.get_reload_delay()

    if delay > 0:
        time = timeutils.string(delay, message.db_user, granularity=1)
        msg = message.db_chat.get_message('please_wait', time=time)

        await message.reply_text(msg)
    else:
        chat = await message.db_chat.reload(client)

        msg = chat.get_message('reload_top')

        msg += '\n\n' + chat.get_message('reloaded_admins', amount=len(chat.administrators))
        msg += '\n' + chat.get_message('has_perms' if chat.has_permissions else 'no_perms')

        await message.reply_text(msg)


@Client.on_message(filters.private & filters.command(['reload', 'riavvia']))
async def on_reload_private(_, message):
    await message.reply_text(message.db_user.get_message('group_only_command'))
