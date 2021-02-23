from plate import emojipedia
from pyrogram import Client, filters

from db.models import *


def create_message(settings) -> str:
    chat = settings.chat

    timeout_type = chat.get_setting('timeout_type') or TimeoutType.DISABLED

    if timeout_type != TimeoutType.DISABLED:
        seconds = int(chat.get_setting('timeout_seconds', Timeout.DEFAULT_SECONDS))
        time_string = timeutils.string(seconds, chat, granularity=100)
        type_string = chat.get_message(f'timeout_{timeout_type}')
    else:
        time_string = chat.get_message('timeout_disabled')
        type_string = chat.get_message('timeout_disabled')

    return chat.get_message('timeout_message', time=time_string, type=type_string)


def create_keyboard(settings) -> InlineKeyboardMarkup:
    chat = settings.chat
    keyboard = []

    timeout_type = chat.get_setting('timeout_type') or TimeoutType.DISABLED

    if timeout_type == TimeoutType.DISABLED:
        keyboard.append([InlineKeyboardButton(
            chat.get_message('enable'),
            callback_data=f'timeout_toggle_{settings.id}'
        )])
    else:
        disable_button = InlineKeyboardButton(
            chat.get_message('disable'),
            callback_data=f'timeout_toggle_{settings.id}'
        )

        other_type = TimeoutType.ON_JOIN if timeout_type == TimeoutType.ON_CAPTCHA else TimeoutType.ON_CAPTCHA

        type_button = InlineKeyboardButton(
            chat.get_message(other_type),
            callback_data=f'timeout_type_{settings.id}_{other_type}'
        )

        keyboard.append([disable_button, type_button])

        seconds = int(chat.get_setting('timeout_seconds', Timeout.DEFAULT_SECONDS))

        reset = InlineKeyboardButton(chat.get_message('reset'),
                                     callback_data=f'st_{settings.id}_{Timeout.DEFAULT_SECONDS}')

        keyboard.append([reset])

        d = []

        for a in reversed(timeutils.INTERVALS):
            k, v = a

            if k in ('seconds', 'minutes'):
                d.append((chat.get_message(k, count=3)[2:], v))

        for name, value in d:
            plus = InlineKeyboardButton(emojipedia.PLUS_SIGN, callback_data=f'st_{settings.id}_{seconds + value}')
            n_button = InlineKeyboardButton(name.capitalize(), callback_data='none')
            minus = InlineKeyboardButton(emojipedia.MINUS_SIGN, callback_data=f'st_{settings.id}_{seconds - value}')

            keyboard.append([minus, n_button, plus])

    keyboard.append([InlineKeyboardButton(chat.get_message('back'), callback_data=f'settings_{settings.id}')])

    return InlineKeyboardMarkup(keyboard)


def get_message_data(settings) -> dict:
    return dict(text=create_message(settings), reply_markup=create_keyboard(settings))


@Client.on_callback_query(filters.regex('^timeout_menu_'))
async def on_timeout_menu(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        await callback.answer()
        await callback.edit_message_text(**get_message_data(settings))


@Client.on_callback_query(filters.regex('^st_'))
async def on_set_timeout(_, callback):
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

        if seconds < 30:
            await callback.answer(emojipedia.CROSS_MARK)
            return

        settings.chat.set_setting('timeout_seconds', seconds)

        await callback.answer(emojipedia.CHECK_MARK_BUTTON)
        await callback.edit_message_text(**get_message_data(settings))


@Client.on_callback_query(filters.regex('^timeout_type_'))
async def on_change_timeout_type(_, callback):
    data = callback.data.split('_')
    settings_id = int(data[2])
    timeout_type = '_'.join(data[3:])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        settings.chat.set_setting('timeout_type', timeout_type)

        await callback.answer(emojipedia.CHECK_MARK_BUTTON)
        await callback.edit_message_text(**get_message_data(settings))


@Client.on_callback_query(filters.regex('^timeout_toggle_'))
async def on_toggle_timeout(_, callback):
    data = callback.data.split('_')
    settings_id = int(data[2])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        current = settings.chat.get_setting('timeout_type') or TimeoutType.DISABLED

        if current == TimeoutType.DISABLED:
            settings.chat.set_setting('timeout_type', TimeoutType.ON_CAPTCHA)
        else:
            settings.chat.get_setting('timeout_type', TimeoutType.DISABLED)

        await callback.answer(emojipedia.CHECK_MARK_BUTTON)
        await callback.edit_message_text(**get_message_data(settings))
