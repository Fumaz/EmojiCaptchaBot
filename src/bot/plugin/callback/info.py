from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from util import config


@Client.on_callback_query(filters.regex('^bot_info$'))
async def on_bot_info(_, callback):
    msg = callback.db_user.get_message('info_message', creator=config.CREATOR)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(callback.db_user.get_message('back'),
                                                           callback_data='main_menu')]])

    await callback.answer()
    await callback.edit_message_text(msg, reply_markup=keyboard,
                                     disable_web_page_preview=True)
