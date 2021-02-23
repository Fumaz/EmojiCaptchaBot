# Emoji Captcha 🔒
This bot was created as a way for group administrators to protect themselves from userbots and spammers.<br>
It is entirely made in Python and is **extremely** customizable. Every setting is editable within the group itself and even the background can be changed.

### How it works
Once you've added the bot to your group and given it administrator permissions, it will start listening for new members.<br>
When a new member joins the group, they will be asked to complete a **short** and **simple** captcha (either in the group or in private chat, depending on the settings of the group), the captcha is extremely easy for humans to complete, but almost **impossible** for bots! It also takes very little time to complete (10-20 seconds at most).

### Is it customizable?
Yes! Emoji Captcha is **100%** customizable. You can modify...
- The language of the bot.
- If the bot should send a captcha to users who already completed one after they rejoin.
- The amount of mistakes a user is allowed to make within the captcha.
- The background image of the captcha.
- Where to send the captcha, either in private chat or directly in the group.
- The amount of time a user has to wait after they've failed a captcha to rejoin the group.
- The amount of time a user has to complete the captcha before they automatically fail it.

If you have any other setting you would like me to add, just ask!

### Can I host it myself?
Yes once again! The bot is **completely** open source, and it's very simple to host it on your own.<br>
First, you will need to rename the `config.sample.py` file you can find in src/util/ to `config.py`. Afterwards, edit the file with your bot's details.<br>
All you need to do now is install `docker` and `docker-compose` if you haven't yet, and then run `docker-compose up -d`!
