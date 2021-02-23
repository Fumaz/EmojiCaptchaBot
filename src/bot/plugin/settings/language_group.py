from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified

from db.models import *


@Client.on_callback_query(filters.regex('^change_lg_'))
async def on_change_language(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        await callback.answer()
        await callback.edit_message_text(**languages.create_message_data(callback.db_user, settings.chat, settings))


@Client.on_callback_query(filters.regex('^language_g_'))
async def on_language_selected(_, callback):
    data = callback.data.split('_')[2:]
    settings_id = int(data[0])
    language = '_'.join(data[1:])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        settings.chat.language = language
        await callback.answer(settings.chat.get_message('language_selected', flag=settings.chat.get_message('flag')),
                              show_alert=True)

        try:
            await callback.edit_message_text(**languages.create_message_data(callback.db_user, settings.chat, settings))
        except MessageNotModified:  # If the user selects the same language he already had
            pass
