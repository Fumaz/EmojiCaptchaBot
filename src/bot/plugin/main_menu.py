from pyrogram import Client, filters

from bot.plugin.settings import settings_menu
from db.models import *
from web import web


def create(user) -> dict:
    msg = user.get_message('main_menu',
                           mention=user.mention,
                           image=formatting.invisible_link(web.get_url('menu.png', 'banners')))

    add_to_group = InlineKeyboardButton(user.get_message('add_to_group'),
                                        url=formatting.deepgroup('added'))

    test_captcha = InlineKeyboardButton(user.get_message('test_captcha'),
                                        callback_data='test_captcha')

    support = InlineKeyboardButton(user.get_message('support'),
                                   url=f'https://t.me/Fumaz')

    info = InlineKeyboardButton(user.get_message('info'),
                                callback_data='bot_info')

    language = InlineKeyboardButton(user.get_message('language', flag=user.get_message('flag')),
                                    callback_data='change_language_private')

    keyboard = InlineKeyboardMarkup([[add_to_group], [test_captcha, support], [language, info]])

    return dict(text=msg, reply_markup=keyboard, disable_web_page_preview=False)


@Client.on_message(filters.command('start') & filters.private)
async def on_main_menu_command(client, message):
    args = message.command[1:]

    if len(args) > 0:
        arg = args[0]

        if arg.startswith('settings_'):
            chat_id = arg.split('_')[1]
            with db_session:
                chat = Chat.get(id=chat_id)

                if message.db_user.id not in chat.administrators and not message.db_user.is_admin:
                    await message.reply_text(message.db_user.get_message('not_admin'))
                    return

                user = message.db_user.current
                settings = SettingsInstance(chat=chat, opener=user)
                commit()

                user.reset_action()

                await message.reply_text(**settings_menu.get_message_data(settings))
                return
        elif arg.startswith('verify_'):
            token_id = arg.split('_')[1]
            with db_session:
                token = VerificationToken.get(id=token_id)

                if not token or token.user.id != message.db_user.id:
                    await message.reply_text(token.user.get_message('not_for_you'))
                else:
                    await token.use(client, restrict=False)

            return

    await message.reply_text(**create(message.db_user))


@Client.on_callback_query(filters.regex('^main_menu$'))
async def on_main_menu_callback(_, callback):
    await callback.answer()
    await callback.edit_message_text(**create(callback.db_user))
