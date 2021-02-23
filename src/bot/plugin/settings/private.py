from pyrogram import Client, filters

from db.models import *
from web import web


@db_session
def create_keyboard(user) -> InlineKeyboardMarkup:
    chats = Chat.select(lambda c: c.type != ChatType.CHANNEL and user.id in c.administrators)
    keyboard = []

    for chat in chats:
        keyboard.append([InlineKeyboardButton(chat.title, callback_data=f'osettings_{chat.id}')])

    return InlineKeyboardMarkup(keyboard)


@Client.on_message(filters.private & filters.command(['settings', 'impostazioni']))
async def on_settings_private(_, message):
    msg = message.db_user.get_message('settings_choose_group',
                                      image=formatting.invisible_link(web.get_url('settings.png', 'banners')))
    keyboard = create_keyboard(message.db_user)

    await message.reply_text(msg, reply_markup=keyboard)
