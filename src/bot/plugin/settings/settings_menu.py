from pyrogram import Client, filters

from bot import cfilters
from db.models import *
from web import web


def create_message(settings) -> str:
    chat = settings.chat

    return chat.get_message('settings_menu',
                            mention=chat.mention,
                            image=formatting.invisible_link(web.get_url('settings.png', 'banners')))


def create_keyboard(settings) -> InlineKeyboardMarkup:
    chat = settings.chat

    language = InlineKeyboardButton(
        chat.get_message('language', flag=chat.get_message('flag')),
        callback_data=f'change_lg_{settings.id}'
    )

    verify_rejoins = InlineKeyboardButton(
        chat.get_message('verify_rejoins', status=boolutils.to_emoji(chat.get_bool_setting('verify_rejoins'))),
        callback_data=f'toggle_vr_{settings.id}'
    )

    allowed_mistakes = InlineKeyboardButton(
        chat.get_message('allowed_mistakes'),
        callback_data=f'change_am_{settings.id}'
    )

    background = InlineKeyboardButton(
        chat.get_message('background'),
        callback_data=f'bg_menu_{settings.id}'
    )

    verification_type = InlineKeyboardButton(
        chat.get_message('verification_type'),
        callback_data=f'vt_menu_{settings.id}'
    )

    delay = InlineKeyboardButton(
        chat.get_message('delay'),
        callback_data=f'delay_menu_{settings.id}'
    )

    timeout = InlineKeyboardButton(
        chat.get_message('timeout'),
        callback_data=f'timeout_menu_{settings.id}'
    )

    close = InlineKeyboardButton(
        chat.get_message('close'),
        callback_data=f'close_settings_{settings.id}'
    )

    return InlineKeyboardMarkup([
        [language, verify_rejoins],
        [allowed_mistakes, background],
        [verification_type, delay],
        [timeout],
        [close]
    ])


def get_message_data(settings) -> dict:
    return dict(text=create_message(settings),
                reply_markup=create_keyboard(settings),
                disable_web_page_preview=False)


@Client.on_callback_query(filters.regex('^osettings_'))
async def on_open_settings(_, callback):
    chat_id = int(callback.data.split('_')[1])

    with db_session:
        chat = Chat.get(id=chat_id)

        if callback.db_user.id not in chat.administrators and not callback.db_user.is_admin:
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        user = callback.db_user.current
        settings = SettingsInstance(chat=chat, opener=user)
        commit()

        user.reset_action()

        await callback.answer()
        await callback.edit_message_text(**get_message_data(settings))


@Client.on_callback_query(filters.regex('^settings_'))
async def on_settings_menu(_, callback):
    settings_id = int(callback.data.split('_')[1])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        user.reset_action()

        await callback.answer()
        await callback.edit_message_text(**get_message_data(settings))


@Client.on_callback_query(filters.regex('^close_settings_'))
async def on_close_settings(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        user = callback.db_user.current
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        user.reset_action()

        await callback.answer()
        await callback.message.delete()

        if callback.message.reply_to_message:
            try:
                callback.message.reply_to_message.delete()
            except RPCError:
                pass


@Client.on_message(cfilters.group_command(['settings', 'impostazioni']) & (cfilters.chat_admin | cfilters.bot_admin))
async def on_settings_command(_, message):
    chat = message.db_chat

    if not chat.has_permissions:
        await message.reply_text(chat.get_message('bot_not_admin'))
        return

    msg = chat.get_message('where_open_settings')
    here = InlineKeyboardButton(chat.get_message('here'),
                                callback_data=f'osettings_{chat.id}')
    private = InlineKeyboardButton(chat.get_message('private'),
                                   url=formatting.deeplink(f'settings_{chat.id}'))

    await message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[here], [private]]))


async def update(callback, settings):
    await callback.edit_message_text(**get_message_data(settings))
