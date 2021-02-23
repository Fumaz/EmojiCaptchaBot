from pyrogram import Client, filters, emoji
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def unbanned_keyboard(chat) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(chat.get_message('unbanned'),
                                                       callback_data='unbanned')]])


def unban_keyboard(chat, user) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(chat.get_message('unban'),
                                                       callback_data=f'unban_{user.id}')]])


@Client.on_callback_query(filters.regex('^unban_'))
async def on_unban(client: Client, callback):
    from db.models import User, Chat, db_session

    with db_session:
        data = callback.data.split('_')[1:]
        chat = callback.message.chat
        user_id = int(data[0])

        db_chat = await Chat.from_pyrogram(chat)
        db_target = User.get(id=user_id)
        db_user = callback.db_user

        if db_user.id in db_chat.administrators and db_chat.has_permissions:
            await callback.answer()

            await client.unban_chat_member(chat_id=db_chat.id, user_id=db_target.id)
            await callback.edit_message_reply_markup(unbanned_keyboard(db_chat))
        else:
            await callback.answer(emoji.CROSS_MARK, show_alert=True)
