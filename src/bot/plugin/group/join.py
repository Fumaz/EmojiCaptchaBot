from pyrogram import Client, filters

from bot import cfilters
from db.models import *


@Client.on_message(filters.new_chat_members & cfilters.has_permissions & ~cfilters.self_was_added)
async def on_join_has_permissions(client, message):
    with db_session:
        db_chat = message.db_chat.current
        db_users = message.db_new_chat_members

        verify_rejoins = db_chat.get_bool_setting('verify_rejoins')

        for user in db_users:
            user = user.current

            if not user.is_bot and (verify_rejoins or user not in db_chat.verified_users):
                await Captcha.verify_wait(client, db_chat, user, message)


@Client.on_message(filters.new_chat_members & ~cfilters.has_permissions & ~cfilters.self_was_added)
async def on_join_no_permissions(client, message):
    db_chat = message.db_chat

    if db_chat.type == ChatType.SUPERGROUP:
        db_chat = await message.db_chat.reload(client=client, update_date=False)

        if db_chat.has_permissions:
            await on_join_has_permissions(client, message)
            return

    await message.reply_text(message.db_chat.get_message('missing_permissions'))


@Client.on_callback_query(filters.regex('^verify_'))
async def on_verify_callback(client, callback):
    db_user = callback.db_user
    db_chat = callback.db_chat
    data = callback.data.split('_')[1:]
    token_id = data[0]

    if not db_user or not db_chat:
        return

    with db_session:
        token = VerificationToken.get(id=token_id)

        if not token or token.user.id != db_user.id or token.chat.id != db_chat.id:
            await callback.answer(db_chat.get_message('not_for_you'), show_alert=True)
            return

        db_user = db_user.current
        db_chat = db_chat.current

        if not db_chat.get_bool_setting('verify_rejoins') and db_user in db_chat.verified_users:
            await callback.message.delete()

            try:
                await client.restrict_chat_member(chat_id=db_chat.id, user_id=db_user.id,
                                                  permissions=types.ChatPermissions(can_send_messages=True))
            except:
                pass
            return

        await token.use(client, message=callback.message.reply_to_message, restrict=False)
