import os

from PIL import Image
from pyrogram import Client, filters

from bot import cfilters
from db.models import *
from web import web


def create_message(settings) -> str:
    chat = settings.chat
    background = chat.get_setting('background', default=creator.DEFAULT_BACKGROUND)

    return chat.get_message('background_message',
                            image=formatting.invisible_link(web.get_url(background, 'backgrounds')))


def create_keyboard(settings) -> InlineKeyboardMarkup:
    chat = settings.chat

    change = InlineKeyboardButton(chat.get_message('change'),
                                  callback_data=f'change_bg_{settings.id}')

    reset = InlineKeyboardButton(chat.get_message('reset'),
                                 callback_data=f'reset_bg_{settings.id}')

    back = InlineKeyboardButton(chat.get_message('back'),
                                callback_data=f'settings_{settings.id}')

    return InlineKeyboardMarkup([[change, reset], [back]])


def create_message_data(settings) -> dict:
    return dict(text=create_message(settings), reply_markup=create_keyboard(settings),
                disable_web_page_preview=False)


@Client.on_callback_query(filters.regex('^bg_menu_'))
async def on_background_menu(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        callback.db_user.reset_action()

        await callback.answer()
        await callback.edit_message_text(**create_message_data(settings))


@Client.on_callback_query(filters.regex('^change_bg_'))
async def on_change_background(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        msg = settings.chat.get_message('send_new_background', mention=callback.db_user.mention)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(settings.chat.get_message('back'),
                                                               callback_data=f'bg_menu_{settings.id}')]])

        callback.db_user.set_action(f'change_background_{settings.id}')

        await callback.answer()
        await callback.edit_message_text(msg, reply_markup=keyboard)


@Client.on_callback_query(filters.regex('^reset_bg_'))
async def on_reset_background(_, callback):
    settings_id = int(callback.data.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(callback.db_user):
            await callback.answer(callback.db_user.get_message('not_admin'), show_alert=True)
            return

        settings.chat.remove_setting('background')

        await callback.answer()
        await callback.edit_message_text(**create_message_data(settings))


@Client.on_message(filters.photo & cfilters.action_regex('^change_background_'))
async def on_send_new_background(_, message):
    settings_id = int(message.db_user.action.split('_')[2])

    with db_session:
        settings = SettingsInstance.get(id=settings_id)

        if not settings or not settings.can_edit(message.db_user):
            message.db_user.reset_action()
            return

        downloaded = await message.download()
        resized = Image.open(downloaded).convert('RGBA').resize((532, 380), Image.ANTIALIAS)

        while True:
            new_background = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) + '.png'

            if not os.path.exists(os.path.join(config.BACKGROUNDS_DIR, new_background)):
                break

        resized.save(os.path.join(config.BACKGROUNDS_DIR, new_background), "PNG")

        old_background = settings.chat.get_setting('background')

        if old_background:
            os.remove(os.path.join(config.BACKGROUNDS_DIR, old_background))

        settings.chat.set_setting('background', new_background)

        if message.reply_to_message:
            try:
                await message.reply_to_message.delete()
            except RPCError:
                pass

        await message.reply_text(**create_message_data(settings))
