from pyrogram import Client, filters

from db.models import *

captcha_callback = filters.regex('^c_')


@Client.on_callback_query(captcha_callback)
async def on_guess_callback(client, callback):
    with db_session:
        data = callback.data.split('_')[1:]

        captcha_id = data[0]
        emoji_id = int(data[1])

        captcha = Captcha.get(id=captcha_id)

        localizator = callback.db_chat or callback.db_user

        if callback.db_user.id != captcha.user.id:
            await callback.answer(localizator.get_message('not_for_you'), show_alert=True)
            return

        captcha.guess_from_id(emoji_id)

        await callback.answer()
        await captcha.update_message(callback.message, client)
