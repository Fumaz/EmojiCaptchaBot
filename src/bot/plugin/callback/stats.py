from pyrogram import Client, filters

from db.models import *


@Client.on_callback_query(filters.regex('^stats$'))
async def on_stats(_, callback):
    with db_session:
        users = User.select().count() + sum(select(c.members_count for c in Chat))
        groups = Chat.select().count()
        captchas = Captcha.select().count()

    message = callback.db_user.get_message('stats_message', users=users, groups=groups, captchas=captchas)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(callback.db_user.get_message('back'),
                                                           callback_data='main_menu')]])

    await callback.answer()
    await callback.edit_message_text(message, reply_markup=keyboard)
