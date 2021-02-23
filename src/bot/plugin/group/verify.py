from pyrogram import Client, filters

from bot import cfilters
from db.models import User, Captcha


@Client.on_message(cfilters.group_command(['verify', 'captcha', 'verifica']) & cfilters.chat_admin)
async def on_verify(client, message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text(message.db_chat.get_message('reply_to_message'))
        return

    if not message.db_chat.has_permissions:
        await message.reply_text(message.db_chat.get_message('bot_not_admin'))
        return

    user = message.reply_to_message.from_user
    target = await User.from_pyrogram(message.reply_to_message.from_user)
    member = await client.get_chat_member(chat_id=message.chat.id, user_id=user.id)

    if target.is_bot:
        await message.reply_text(message.db_chat.get_message('cannot_verify_bots'))
        return
    elif target.is_admin:
        await message.reply_text(message.db_chat.get_message('cannot_verify_bot_admin'))
        return
    elif member.status == 'administrator' or member.status == 'creator':
        await message.reply_text(message.db_chat.get_message('cannot_verify_admins'))
        return

    await Captcha.verify_wait(client, message.db_chat, target, message.reply_to_message)


@Client.on_message(filters.private & filters.command('verify'))
async def on_verify_private(_, message):
    await message.reply_text(message.db_user.get_message('group_only_command'))
