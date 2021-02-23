from plate import emojipedia
from pyrogram import Client, filters

from db.models import *


def create_keyboard(settings) -> InlineKeyboardMarkup:
    amount = settings.chat.get_setting('allowed_mistakes')

    if not amount:
        amount = config.DEFAULT_ALLOWED_MISTAKES
    else:
        amount = int(amount)

    plus_one = InlineKeyboardButton(emojipedia.PLUS_SIGN,
                                    callback_data=f'am_{settings.id}_{amount + 1}')

    current = InlineKeyboardButton(str(amount),
                                   callback_data='none')

    minus_one = InlineKeyboardButton(emojipedia.MINUS_SIGN,
                                     callback_data=f'am_{settings.id}_{amount - 1}')
    reset = InlineKeyboardButton(settings.chat.get_message('reset'),
                                 callback_data=f'am_{settings.id}_{config.DEFAULT_ALLOWED_MISTAKES}')

    back = InlineKeyboardButton(settings.chat.get_message('back'),
                                callback_data=f'settings_{settings.id}')

    return InlineKeyboardMarkup([[minus_one, current, plus_one], [reset], [back]])


def create_message(settings) -> str:
    chat = settings.chat

    amount = chat.get_setting('allowed_mistakes')

    if not amount:
        amount = config.DEFAULT_ALLOWED_MISTAKES
    else:
        amount = int(amount)

    return chat.get_message('allowed_mistakes_message', amount=amount)


def create_message_data(settings) -> dict:
    return dict(text=create_message(settings), reply_markup=create_keyboard(settings))


@Client.on_callback_query(filters.regex('^change_am_'))
async def on_change_allowed_mistakes(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        await callback.answer()
        await callback.edit_message_text(**create_message_data(settings))


@Client.on_callback_query(filters.regex('^am_'))
async def on_edit_allowed_mistakes(_, callback):
    data = callback.data.split('_')[1:]
    settings_id = int(data[0])
    amount = int(data[1])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        if amount < 0 or amount > 10:
            await callback.answer(settings.chat.get_message('allowed_mistakes_cannot_be', amount=amount),
                                  show_alert=True)
            return

        settings.chat.set_setting('allowed_mistakes', amount)

        await callback.answer()
        await callback.edit_message_text(**create_message_data(settings))
