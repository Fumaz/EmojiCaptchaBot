from bot import bot
from captcha import creator
from db import models
from web import web

if __name__ == '__main__':
    creator.setup()
    models.setup()
    web.run()
    bot.run()
