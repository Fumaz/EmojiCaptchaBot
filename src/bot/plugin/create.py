from pyrogram import Client, filters

from bot import cfilters
from db.models import *


@Client.on_message(filters.command('newcaptcha') & filters.private & cfilters.bot_admin)
async def on_new_captcha(client, message):
    captcha = Captcha.generate(message.db_user)

    await captcha.send_message(client)
