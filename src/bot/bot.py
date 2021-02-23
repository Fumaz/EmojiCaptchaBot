from pyrogram import Client

from util import config

client = Client(session_name=config.SESSION_NAME,
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                bot_token=config.BOT_TOKEN,
                workers=16,
                plugins=dict(root=config.PLUGINS_DIR))


def run():
    client.run()
