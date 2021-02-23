from plate import emojipedia
from pyrogram import Client, filters

from db.models import *


def create_message(settings) -> str:
    chat = settings.chat

    delay = int(chat.get_setting('captcha_delay', Captcha.DEFAULT_DELAY))
    time_string = timeutils.string(delay, chat, granularity=100) if delay > 30 else chat.get_message('no_delay')

    return chat.get_message('delay_message', time=time_string)


def create_keyboard(settings) -> InlineKeyboardMarkup:
    chat = settings.chat
    delay = int(chat.get_setting('captcha_delay', Captcha.DEFAULT_DELAY))

    keyboard = []

    reset = InlineKeyboardButton(chat.get_message('reset'),
                                 callback_data=f'sd_{settings.id}_{Captcha.DEFAULT_DELAY}')

    no_delay = InlineKeyboardButton(chat.get_message('no_delay'),
                                    callback_data=f'sd_{settings.id}_0')

    keyboard.append([reset, no_delay])

    d = []

    for a in reversed(timeutils.INTERVALS):
        k, v = a

        if k in ('minutes', 'hours', 'days'):
            d.append((chat.get_message(k, count=3)[2:], v))

    for name, value in d:
        plus = InlineKeyboardButton(emojipedia.PLUS_SIGN, callback_data=f'sd_{settings.id}_{delay + value}')
        n_button = InlineKeyboardButton(name.capitalize(), callback_data='none')
        minus = InlineKeyboardButton(emojipedia.MINUS_SIGN, callback_data=f'sd_{settings.id}_{delay - value}')

        keyboard.append([minus, n_button, plus])

    keyboard.append([InlineKeyboardButton(chat.get_message('back'), callback_data=f'settings_{settings.id}')])

    return InlineKeyboardMarkup(keyboard)


def get_message_data(settings) -> dict:
    return dict(text=create_message(settings), reply_markup=create_keyboard(settings))


@Client.on_callback_query(filters.regex('^delay_menu_'))
async def on_delay_menu(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        await callback.answer()
        await callback.edit_message_text(**get_message_data(settings))


@Client.on_callback_query(filters.regex('^sd_'))
async def on_set_delay(_, callback):
    data = callback.data.split('_')
    settings_id = int(data[1])
    seconds = int(data[2])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        if seconds > timeutils.INTERVALS[0][1]:
            await callback.answer(emojipedia.CROSS_MARK)
            return

        settings.chat.set_setting('captcha_delay', seconds)

        await callback.answer(emojipedia.CHECK_MARK_BUTTON)
        await callback.edit_message_text(**get_message_data(settings))
