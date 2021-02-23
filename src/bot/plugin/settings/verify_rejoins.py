from pyrogram import Client, filters

from bot.plugin.settings import settings_menu
from db.models import *


@Client.on_callback_query(filters.regex('^toggle_vr_'))
async def on_toggle_verify_rejoins(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        current = settings.chat.get_bool_setting('verify_rejoins')
        settings.chat.set_setting('verify_rejoins', not current)

        await callback.answer(settings.chat.get_message('verify_rejoins_' + ('disabled' if current else 'enabled')),
                              show_alert=True)

        await settings_menu.update(callback, settings)
