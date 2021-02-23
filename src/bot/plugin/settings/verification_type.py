from plate import emojipedia
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified

from db.models import *


def create_message(settings) -> str:
    chat = settings.chat
    current = chat.get_setting('verification_type', TokenDestination.GROUP)

    return chat.get_message('verification_type_message', current=current)


def create_keyboard(settings) -> InlineKeyboardMarkup:
    chat = settings.chat

    private = InlineKeyboardButton(chat.get_message('private'),
                                   callback_data=f'change_vt_{settings.id}_PRIVATE')

    group = InlineKeyboardButton(chat.get_message('group'),
                                 callback_data=f'change_vt_{settings.id}_GROUP')

    back = InlineKeyboardButton(chat.get_message('back'),
                                callback_data=f'settings_{settings.id}')

    return InlineKeyboardMarkup([[private, group], [back]])


def create_message_data(settings) -> dict:
    return dict(text=create_message(settings), reply_markup=create_keyboard(settings))


@Client.on_callback_query(filters.regex('^vt_menu_'))
async def on_verification_type_menu(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        await callback.answer()
        await callback.edit_message_text(**create_message_data(settings))


@Client.on_callback_query(filters.regex('^change_vt_'))
async def on_change_verification_type(_, callback):
    data = callback.data.split('_')[2:]
    settings_id = int(data[0])
    token_destination = data[1].upper()

    if not getattr(TokenDestination, token_destination):
        await callback.answer(callback.db_user.get_message('error'), show_alert=True)
        return

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        settings.chat.set_setting('verification_type', token_destination)

        await callback.answer(emojipedia.CHECK_MARK_BUTTON, show_alert=True)

        try:
            await callback.edit_message_text(**create_message_data(settings))
        except MessageNotModified:
            pass
