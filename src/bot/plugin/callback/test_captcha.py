from pyrogram import Client, filters

from db.models import Captcha


@Client.on_callback_query(filters.regex('^test_captcha$'))
async def on_test_captcha(client, callback):
    await callback.answer()

    captcha = Captcha.generate(callback.db_user)

    await captcha.send_message(client)
