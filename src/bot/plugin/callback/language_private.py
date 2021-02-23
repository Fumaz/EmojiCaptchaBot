from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified

from db.models import *


@Client.on_callback_query(filters.regex('^change_language_private$'))
async def on_change_language(_, callback):
    await callback.answer()
    await callback.edit_message_text(**languages.create_message_data(callback.db_user))


@Client.on_callback_query(filters.regex('^language_p_'))
async def on_language_selected(_, callback):
    language = '_'.join(callback.data.split('_')[2:])

    with db_session:
        user = callback.db_user.current
        user.language = language

        await callback.answer(user.get_message('language_selected', flag=user.get_message('flag')), show_alert=True)

        try:
            await callback.edit_message_text(**languages.create_message_data(user))
        except MessageNotModified:  # If the user selects the same language he already had
            pass
