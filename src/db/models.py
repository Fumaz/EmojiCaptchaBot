import io
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Union

import pyrogram
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pony.orm import *
from pyrogram import types
from pyrogram.errors import RPCError, FloodWait
from pyrogram.methods.chats.iter_chat_members import Filters
from pyrogram.raw.functions.messages import MigrateChat
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.plugin.group import unban
from captcha import creator
from localization import languages, timeutils
from util import config, formatting, boolutils

db = Database()


def random_string(k: int = 1):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=k))


def generate_code(db_obj: db.Entity, property_name: str = 'id',
                  min_length: int = 5, max_length: int = 8) -> str:
    while True:
        code = random_string(k=random.randint(min_length, max_length))

        if not db_obj.get(**{property_name: code}):
            break

    return code


# noinspection PyTypeChecker
def captcha_code() -> str:
    return generate_code(Captcha)


# noinspection PyTypeChecker
def token_code() -> str:
    return generate_code(VerificationToken)


# noinspection PyTypeChecker
def report_code() -> str:
    return generate_code(BugReport)


class BugReportStatus:
    OPEN = 'OPEN'
    FIXED = 'FIXED'
    CLOSED = 'CLOSED'


class CaptchaStatus:
    WAITING = 'waiting'
    COMPLETED = 'completed'
    LOST = 'lost'
    INVALID = 'invalid'


class TokenStatus:
    WAITING = 'waiting'
    EXPIRED = 'expired'
    USED = 'used'


class TokenDestination:
    PRIVATE = 'PRIVATE'
    GROUP = 'GROUP'


class TimeoutType:
    DISABLED = 'disabled'
    ON_JOIN = 'on_join'
    ON_CAPTCHA = 'on_captcha'


class GuessResult:
    INVALID = 'invalid'
    CORRECT = 'correct'
    INCORRECT = 'incorrect'


class ChatType:
    GROUP = 'group'
    CHANNEL = 'channel'
    SUPERGROUP = 'supergroup'


class User(db.Entity):
    id = PrimaryKey(int)
    first_name = Required(str)
    last_name = Optional(str)
    username = Optional(str)
    language = Required(str)
    action = Optional(str)
    dc_id = Optional(int)
    is_active = Required(bool, default=True)
    is_admin = Required(bool, default=False)
    is_banned = Required(bool, default=False)
    is_vip = Required(bool, default=False)
    is_bot = Required(bool)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    captchas = Set('Captcha')
    tokens = Set('VerificationToken')
    settings = Set('UserSetting')
    verified_chats = Set('Chat', reverse='verified_users')
    opened_settings = Set('SettingsInstance')

    def before_update(self):
        self.last_update = datetime.now()

    @staticmethod
    async def from_pyrogram(tg_user: Union[types.User, types.Message,
                                           types.InlineQuery, types.ChosenInlineResult,
                                           types.CallbackQuery]) -> Union['User', None]:
        with db_session:
            if not isinstance(tg_user, types.User):
                tg_user = tg_user.from_user

            if not tg_user:
                return None

            user_id = tg_user.id
            first_name = tg_user.first_name
            last_name = tg_user.last_name or ''
            username = tg_user.username or ''
            language = languages.get_nearest(tg_user.language_code)
            dc_id = tg_user.dc_id
            is_bot = tg_user.is_bot

            db_user: User = User.get(id=tg_user.id)

            if not db_user:
                db_user = User(id=user_id,
                               first_name=first_name,
                               last_name=last_name,
                               username=username,
                               language=language,
                               is_bot=is_bot,
                               dc_id=dc_id)

                db_user.is_first_use = True
            else:
                db_user.is_active = True
                db_user.first_name = first_name
                db_user.last_name = last_name
                db_user.username = username
                db_user.dc_id = dc_id or db_user.dc_id

                db_user.is_first_use = False

            db_user.tg = tg_user

        return db_user

    @property
    def full_name(self) -> str:
        return f'{self.first_name}{" " + self.last_name if self.last_name else ""}'

    @property
    def mention(self) -> str:
        return f"<a href='tg://user?id={self.id}'>{self.full_name}</a>"

    @property
    def current(self) -> 'User':
        return User.get(id=self.id)

    def get_message(self, message_name: str, **kwargs) -> 'str':
        return languages.get_message(message_name, self.language, **kwargs)

    @db_session
    def get_setting(self, setting_name: str, default=None) -> Union[str, None]:
        setting = self.current.settings.select(lambda s: s.name == setting_name)

        if len(setting) > 0:
            return setting.first().value
        else:
            return default

    def get_bool_setting(self, setting_name: str) -> bool:
        return boolutils.to_bool(self.get_setting(setting_name))

    @db_session
    def set_action(self, action: str) -> 'User':
        user = self.current
        user.action = action

        return user

    @db_session
    def reset_action(self) -> 'User':
        user = self.current
        user.action = ''

        return user


class Chat(db.Entity):
    id = PrimaryKey(int, size=64)
    title = Required(str)
    username = Optional(str)
    description = Optional(str)
    members_count = Required(int)
    type = Required(str)
    language = Required(str, default='en_US')
    is_verified = Required(bool)
    is_restricted = Required(bool)
    is_scam = Required(bool)
    is_vip = Required(bool, default=False)
    has_permissions = Required(bool, default=False)
    administrators = Required(IntArray, default=[])
    last_reload = Required(datetime, default=datetime.now)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)

    captchas = Set('Captcha')
    tokens = Set('VerificationToken')
    settings = Set('ChatSetting')
    verified_users = Set(User, reverse='verified_chats')
    settings_instances = Set('SettingsInstance')

    RELOAD_DELAY = 30

    def before_update(self):
        self.last_update = datetime.now()

    @staticmethod
    async def from_pyrogram(tg_chat: Union[types.Chat, types.Message, types.CallbackQuery]) -> Union['Chat', None]:
        db_chat = None

        with db_session:
            if isinstance(tg_chat, types.CallbackQuery):
                tg_chat = tg_chat.message.chat if tg_chat.message else None
            elif isinstance(tg_chat, types.Message):
                tg_chat = tg_chat.chat

            if not tg_chat:
                return db_chat

            if not getattr(ChatType, tg_chat.type.upper(), None):
                return db_chat

            chat_id = tg_chat.id
            title = tg_chat.title
            username = tg_chat.username or ''
            description = tg_chat.description or ''
            members_count = tg_chat.members_count or 0
            chat_type = tg_chat.type
            is_verified = tg_chat.is_verified or False
            is_restricted = tg_chat.is_restricted or False
            is_scam = tg_chat.is_scam or False

            db_chat = Chat.get(id=chat_id)

            if not db_chat:
                db_chat = Chat(id=chat_id,
                               title=title,
                               username=username,
                               description=description,
                               members_count=members_count,
                               type=chat_type,
                               is_verified=is_verified,
                               is_restricted=is_restricted,
                               is_scam=is_scam)

                db_chat.is_first_use = True
            else:
                db_chat.title = title
                db_chat.username = username
                db_chat.description = description
                db_chat.type = chat_type
                db_chat.is_verified = is_verified
                db_chat.is_restricted = is_restricted
                db_chat.is_scam = is_scam

                db_chat.is_first_use = False

        return db_chat

    @db_session
    def migrate(self, from_id: int, client: pyrogram.Client) -> 'Chat':
        to_chat = self.current
        from_chat = Chat.get(id=from_id)

        to_chat.language = from_chat.language
        to_chat.is_vip = from_chat.is_vip
        to_chat.has_permissions = self.check_permissions(client)
        to_chat.is_first_use = False

        from_chat.delete()

        return to_chat

    @property
    def current(self) -> 'Chat':
        return Chat.get(id=self.id)

    @property
    def mention(self, tag: str = 'b') -> str:
        if self.username:
            return formatting.html_link(f'https://t.me/{self.username}', self.title)
        else:
            return f'<{tag}>{self.title}</{tag}>'

    @db_session
    def get_setting(self, setting_name: str, default=None) -> Union[str, None]:
        setting = self.current.settings.select(lambda s: s.name == setting_name)

        if len(setting) > 0:
            return setting.first().value
        else:
            return default

    def get_bool_setting(self, setting_name: str) -> bool:
        return boolutils.to_bool(self.get_setting(setting_name))

    @db_session
    def set_setting(self, setting_name: str, value):
        if not isinstance(value, str) and value is not None:
            value = str(value)

        chat = self.current
        setting = chat.settings.select(lambda s: s.name == setting_name)

        if len(setting) > 0:
            setting = setting.first()
        else:
            setting = None

        if not setting:
            if value is None:
                return

            ChatSetting(chat=chat, name=setting_name, value=value)
        else:
            if value is None:
                setting.delete()
                return

            setting.value = value
            setting.last_update = datetime.now()

    def remove_setting(self, setting_name: str):
        self.set_setting(setting_name, None)

    def get_message(self, message_name: str, **kwargs) -> 'str':
        return languages.get_message(message_name, self.language, **kwargs)

    async def check_permissions(self, client: pyrogram.Client):
        chat_id = self.id
        member = await client.get_chat_member(chat_id, 'self')

        return bool(member.can_restrict_members if member.can_restrict_members is not None else
                    member.status == 'administrator')

    async def update_permissions(self, client: pyrogram.Client, session: bool = True):
        async def func():
            chat = self.current

            chat.has_permissions = await chat.check_permissions(client)

        if session:
            with db_session:
                await func()
        else:
            await func()

    async def update_administrators(self, client: pyrogram.Client, session: bool = True):
        async def func():
            chat = self.current

            chat.administrators = [
                member.user.id async for member in client.iter_chat_members(chat_id=chat.id,
                                                                            filter=Filters.ADMINISTRATORS)
            ]

        if session:
            with db_session:
                await func()
        else:
            await func()

    @db_session
    def set_language(self, language: str):
        chat = self.current

        chat.language = language

    def get_reload_delay(self) -> int:
        return int((self.last_reload - datetime.now()).total_seconds())

    async def reload(self, client: pyrogram.Client, update_date: bool = True) -> 'Chat':
        with db_session:
            chat = self.current

            if update_date:
                chat.last_reload = datetime.now() + timedelta(seconds=self.RELOAD_DELAY)

            await chat.update_permissions(client, session=False)
            await chat.update_administrators(client, session=False)
            await chat.update_members(client, session=False)

            if chat.has_permissions:
                if chat.type == ChatType.GROUP:
                    await client.send(MigrateChat(chat_id=chat.id))

            return chat

    async def update_members(self, client: pyrogram.Client, session: bool = True, throw: bool = False):
        async def func():
            chat = self.current

            try:
                chat.members_count = await client.get_chat_members_count(chat_id=chat.id) or chat.members_count
            except Exception as e:
                if throw:
                    raise e
                else:
                    print(e, flush=True)

        if session:
            with db_session:
                await func()
        else:
            await func()


class UserSetting(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Required(User)
    name = Required(str)
    value = Required(str)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)


class ChatSetting(db.Entity):
    id = PrimaryKey(int, auto=True)
    chat = Required(Chat)
    name = Required(str)
    value = Required(str)
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)


class Captcha(db.Entity):
    id = PrimaryKey(str, default=captcha_code)
    user = Required(User)
    chat = Optional(Chat)
    image = Optional(str)
    status = Required(str, default=CaptchaStatus.WAITING)
    token = Optional('VerificationToken')
    message_id = Optional(int)
    total_emojis = Required(StrArray)
    correct_emojis = Required(StrArray)
    guessed_emojis = Required(StrArray, default=[])
    allowed_mistakes = Required(int, default=config.DEFAULT_ALLOWED_MISTAKES)
    timeout = Optional("Timeout")
    last_update = Required(datetime, default=datetime.now)
    creation_date = Required(datetime, default=datetime.now)
    completion_date = Optional(datetime)

    DEFAULT_DELAY = 60 * 60 * 24

    def before_update(self):
        self.last_update = datetime.now()

    @staticmethod
    @db_session
    def generate(user: User, chat: Chat = None) -> 'Captcha':
        user = user.current
        chat = chat.current if chat else None
        background = chat.get_setting('background') if chat else None
        allowed_mistakes = chat.get_setting('allowed_mistakes') if chat else None
        timeout_type = chat.get_setting('timeout_type') if chat else None

        if not timeout_type:
            timeout_type = TimeoutType.DISABLED

        timeout_seconds = chat.get_setting(
            'timeout_seconds') if chat and timeout_type == TimeoutType.ON_CAPTCHA else None

        if not background:
            background = creator.DEFAULT_BACKGROUND

        if not allowed_mistakes:
            allowed_mistakes = config.DEFAULT_ALLOWED_MISTAKES
        else:
            allowed_mistakes = int(allowed_mistakes)

        data = {}

        while True:
            try:
                data = creator.generate(background=background)
                break
            except FileNotFoundError as e:
                print(e)
                continue

        image = data['image']
        total_emojis = data['total']
        correct_emojis = data['correct']

        c = Captcha(user=user, chat=chat,
                    total_emojis=total_emojis,
                    correct_emojis=correct_emojis,
                    allowed_mistakes=allowed_mistakes)

        if timeout_seconds:
            timeout_seconds = int(timeout_seconds or Timeout.DEFAULT_SECONDS)

            timeout = Timeout(captcha=c, seconds=timeout_seconds)
            c.timeout = timeout

        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image.close()

        image_bytes.name = 'captcha.png'
        c.image_bytes = image_bytes

        return c

    @staticmethod
    async def verify_user(client, chat, user, message=None, restrict=True, captcha=None, private: bool = False,
                          token: 'VerificationToken' = None) -> bool:
        try:
            if restrict:
                await client.restrict_chat_member(chat_id=chat.id, user_id=user.id,
                                                  permissions=types.ChatPermissions(can_send_messages=False))

            if not captcha:
                captcha = Captcha.generate(user, chat)

            if token:
                captcha.set_token(token)

            chat_id = user.id if private or not chat else chat.id

            msg = await captcha.send_message(client, chat_id=chat_id,
                                             reply_to_message_id=message.message_id if message else None)
            captcha.set_message(msg)

            if captcha.timeout:
                await captcha.timeout.start(client)

            return True
        except Exception as e:
            print(e, flush=True)
            return False

    @staticmethod
    async def verify_wait(client, chat, user, message=None):
        try:
            await client.restrict_chat_member(chat_id=chat.id, user_id=user.id,
                                              permissions=types.ChatPermissions(can_send_messages=False))

            msg = chat.get_setting('waiting_for_verification')

            if msg:
                msg = msg.format(mention=user.mention)
            else:
                msg = chat.get_message('waiting_for_verification', mention=user.mention)

            button = chat.get_setting('verify_now') or chat.get_message('verify_now')
            destination = getattr(TokenDestination, chat.get_setting('verification_type', TokenDestination.GROUP))
            token = VerificationToken.generate(user, chat, destination=destination)
            button_data = {'text': button}

            if destination == TokenDestination.GROUP:
                button_data['callback_data'] = f'verify_{token.id}'
            elif destination == TokenDestination.PRIVATE:
                button_data['url'] = formatting.deeplink(f'verify_{token.id}')

            msg = await client.send_message(chat.id, text=msg, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(**button_data)]
            ]), reply_to_message_id=message.message_id if message else None)

            token.set_message_id(msg.message_id)
            token.set_reply_to_message_id(message.message_id)

            if token.timeout:
                await token.timeout.start(client)
        except Exception as e:
            raise e

    @property
    def current(self) -> 'Captcha':
        return Captcha.get(id=self.id)

    @property
    def correct_guesses(self) -> set:
        return set(self.guessed_emojis).intersection(self.correct_emojis)

    @property
    def wrong_guesses(self) -> set:
        return set(self.guessed_emojis).difference(self.correct_emojis)

    @property
    def is_correct(self) -> bool:
        return self.status == CaptchaStatus.COMPLETED or set(self.correct_emojis).issubset(self.guessed_emojis)

    @property
    def has_lost(self) -> bool:
        return self.status == CaptchaStatus.LOST or len(self.wrong_guesses) > self.allowed_mistakes

    @property
    def completion_seconds(self) -> int:
        return int((self.completion_date - self.creation_date).total_seconds())

    @db_session
    def set_message(self, message):
        self.current.message_id = message.message_id

    @db_session
    def set_token(self, token):
        self.current.token = token

    async def send_message(self, client: pyrogram.Client,
                           chat_id: int = None,
                           caption: str = None,
                           reply_to_message_id: int = None) -> types.Message:
        with db_session:
            captcha = self.current

            if not chat_id:
                chat_id = captcha.chat.id if captcha.chat else captcha.user.id

            if not caption:
                if captcha.chat:
                    mistakes = captcha.chat.get_message('mistakes', count=captcha.allowed_mistakes)
                else:
                    mistakes = captcha.user.get_message('mistakes', count=captcha.allowed_mistakes)

                kwargs = dict(mention=captcha.user.mention, mistakes=mistakes)

                if captcha.chat:
                    caption = captcha.chat.get_setting('catpcha_caption')

                    if caption:
                        caption = caption.format(**kwargs)

                if not caption:
                    if captcha.chat:
                        caption = captcha.chat.get_message('captcha_caption', **kwargs)
                    else:
                        caption = captcha.user.get_message('captcha_caption', **kwargs)

            return await client.send_photo(chat_id=chat_id,
                                           photo=self.image_bytes,
                                           caption=caption,
                                           reply_to_message_id=reply_to_message_id,
                                           reply_markup=captcha.create_keyboard())

    def create_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[]]
        self.total_emojis: list

        for emoji in self.total_emojis:
            if len(keyboard[-1]) >= 5:
                keyboard.append([])

            text = self.create_button(emoji)
            is_guessed = self.is_guessed(emoji)

            callback_data = f'c_{self.id}_{self.total_emojis.index(emoji)}' if not is_guessed else 'already_guessed'

            keyboard[-1].append(InlineKeyboardButton(text=text, callback_data=callback_data))

        return InlineKeyboardMarkup(keyboard)

    def create_button(self, emoji: str) -> str:
        if emoji in self.guessed_emojis:
            return '✅' if emoji in self.correct_emojis else '❌'
        else:
            return emoji

    def is_guessed(self, emoji: str) -> bool:
        return emoji in self.guessed_emojis

    @db_session
    def guess(self, emoji: str) -> str:
        c = self.current

        if emoji in c.guessed_emojis:
            return GuessResult.INVALID

        if not c.is_latest:
            c.status = CaptchaStatus.INVALID
            return GuessResult.INVALID

        c.guessed_emojis.append(emoji)

        return GuessResult.CORRECT if emoji in c.correct_emojis else GuessResult.INCORRECT

    def guess_from_id(self, emoji_id: int) -> str:
        return self.guess(emoji=self.emoji_from_id(emoji_id))

    @db_session
    def get_status(self) -> str:
        c = self.current

        if c.status == CaptchaStatus.INVALID:
            return c.status

        if c.is_correct:
            c.completion_date = datetime.now()
            c.status = CaptchaStatus.COMPLETED
        elif c.has_lost:
            c.completion_date = datetime.now()
            c.status = CaptchaStatus.LOST

        return c.status

    def emoji_from_id(self, emoji_id: int) -> str:
        return self.total_emojis[emoji_id]

    def is_latest(self) -> bool:
        captcha = self.current

        latest = Captcha.get_latest(captcha.user, captcha.chat)

        return not latest or latest.id == captcha.id

    @staticmethod
    def get_latest(user: User, chat: Chat = None) -> Union['Captcha', None]:
        captchas = Captcha.select(lambda c: c.user == user and c.chat == chat) \
            .order_by(lambda c: desc(c.creation_date)).limit(1)

        if len(captchas) < 1:
            return None

        return captchas.first()

    async def update_message(self, message: types.Message, client: pyrogram.Client) -> types.Message:
        with db_session:
            captcha = self.current
            user = captcha.user
            chat = captcha.chat
            chat_id = None

            status = captcha.get_status()
            reply_to_message_id = message.reply_to_message.message_id if message.reply_to_message else None
            keyboard = None
            should_unban = False

            if status == CaptchaStatus.WAITING:
                message = await message.edit_reply_markup(captcha.create_keyboard())

                return message

            try:
                await message.delete(revoke=True)
            except RPCError:
                pass

            if status == CaptchaStatus.COMPLETED:
                seconds = captcha.completion_seconds
                kwargs = dict(time=timeutils.string(seconds, chat or user, 1), mention=user.mention)

                if chat:
                    group_text = chat.get_setting('captcha_completed')

                    if group_text:
                        group_text = group_text.format(**kwargs)
                    else:
                        group_text = chat.get_message('captcha_completed', **kwargs)
                else:
                    group_text = user.get_message('captcha_completed', **kwargs)

                if self.token and self.token.destination == TokenDestination.PRIVATE:
                    private_text = user.get_message('captcha_completed_private', mention=chat.mention,
                                                    time=timeutils.string(seconds, user, 1))

                    msg = await message.reply_text(private_text, reply_to_message_id=reply_to_message_id,
                                                   disable_web_page_preview=True)
                    chat_id = self.token.chat.id
                    reply_to_message_id = None

                if captcha.chat:
                    captcha.chat.verified_users.add(captcha.user)

                    if captcha.chat.has_permissions:
                        try:
                            await client.restrict_chat_member(chat_id=captcha.chat.id, user_id=captcha.user.id,
                                                              permissions=types.ChatPermissions(can_send_messages=True))
                        except RPCError:
                            pass
            elif status == CaptchaStatus.LOST:
                delay = captcha.chat.get_setting('captcha_delay') if chat else None

                if delay is None:
                    delay = self.DEFAULT_DELAY

                delay = int(delay)

                localizator = captcha.chat or captcha.user

                if delay > 30:
                    time_str = localizator.get_message('in') + ' ' + timeutils.string(delay, localizator, 100)
                else:
                    time_str = localizator.get_message('when_they_rejoin')

                kwargs = dict(time=time_str,
                              mention=captcha.user.mention)

                if captcha.chat:
                    group_text = captcha.chat.get_setting('captcha_incorrect')

                    if group_text:
                        group_text = group_text.format(**kwargs)
                    else:
                        group_text = captcha.chat.get_message('captcha_incorrect', **kwargs)
                else:
                    group_text = captcha.user.get_message('captcha_incorrect', **kwargs)

                if self.token and self.token.destination == TokenDestination.PRIVATE:
                    if delay > 30:
                        time_str = user.get_message('in') + ' ' + timeutils.string(delay, user, 100)
                    else:
                        time_str = user.get_message('when_you_rejoin')

                    private_text = user.get_message('captcha_incorrect_private', mention=chat.mention,
                                                    time=time_str)

                    msg = await message.reply_text(private_text, reply_to_message_id=reply_to_message_id,
                                                   disable_web_page_preview=True)
                    chat_id = self.token.chat.id
                    reply_to_message_id = None

                if captcha.chat and captcha.chat.has_permissions:
                    keyboard = unban.unban_keyboard(captcha.chat, captcha.user)

                    msg = await client.kick_chat_member(chat_id=captcha.chat.id,
                                                        user_id=captcha.user.id,
                                                        until_date=delay if delay >= 30 else 30)

                    if isinstance(msg, types.Message):
                        try:
                            await msg.delete()
                        except RPCError:
                            pass

                    if delay < 30:
                        should_unban = True
                        keyboard = None

            if chat_id:
                await client.delete_messages(chat_id=self.token.chat.id, message_ids=self.token.message_id)

                await client.send_message(chat_id, group_text, reply_to_message_id=self.token.reply_to_message_id,
                                          disable_web_page_preview=True, reply_markup=keyboard)
            else:
                msg = await message.reply_text(group_text, reply_to_message_id=reply_to_message_id,
                                               disable_web_page_preview=True, reply_markup=keyboard)

            if should_unban:
                await client.unban_chat_member(chat_id=captcha.chat.id,
                                               user_id=captcha.user.id)

            return msg


class VerificationToken(db.Entity):
    id = PrimaryKey(str, default=token_code)
    user = Required(User)
    chat = Optional(Chat)
    status = Required(str, default=TokenStatus.WAITING)
    destination = Required(str)
    captcha = Optional(Captcha)
    reply_to_message_id = Optional(int)
    message_id = Optional(int)
    timeout = Optional("Timeout")
    creation_date = Required(datetime, default=datetime.now)
    usage_date = Optional(datetime)

    @staticmethod
    @db_session
    def generate(user: User, chat: Chat = None, destination: str = TokenDestination.PRIVATE) -> 'VerificationToken':
        timeout_type = chat.get_setting('timeout_type') if chat else None

        if not timeout_type:
            timeout_type = TimeoutType.DISABLED

        timeout_seconds = chat.get_setting('timeout_seconds') if chat and timeout_type == TimeoutType.ON_JOIN else None
        timeout = None

        if timeout_seconds:
            timeout_seconds = int(timeout_seconds or Timeout.DEFAULT_SECONDS)
            timeout = Timeout(seconds=timeout_seconds)

        return VerificationToken(user=user.current, chat=chat.current, destination=destination, timeout=timeout)

    @property
    def current(self) -> 'VerificationToken':
        return VerificationToken.get(id=self.id)

    @db_session
    def set_message_id(self, message_id: int):
        self.current.message_id = message_id

    @db_session
    def set_reply_to_message_id(self, reply_to_message_id: int):
        self.current.reply_to_message_id = reply_to_message_id

    async def use(self, client: pyrogram.Client, **kwargs):
        with db_session:
            token = self.current
            token.status = TokenStatus.USED
            token.usage_date = datetime.now()

            if 'message' in kwargs and token.destination == TokenDestination.PRIVATE:
                kwargs['message'] = None

            if token.message_id:
                if token.destination == TokenDestination.PRIVATE:
                    await client.edit_message_text(chat_id=token.chat.id, message_id=token.message_id,
                                                   text=token.chat.get_message('verifying_group',
                                                                               mention=token.user.mention),
                                                   disable_web_page_preview=True)
                else:
                    await client.delete_messages(chat_id=token.chat.id, message_ids=token.message_id)

            result = await Captcha.verify_user(client=client, chat=token.chat, user=token.user,
                                               private=token.destination == TokenDestination.PRIVATE,
                                               token=token, **kwargs)

            if not result:
                await client.send_message(chat_id=token.chat.id, text=token.chat.get_message('missing_permissions'))
                token.chat.has_permissions = False


class SettingsInstance(db.Entity):
    id = PrimaryKey(int, auto=True)
    chat = Required(Chat)
    opener = Optional(User)
    creation_date = Required(datetime, default=datetime.now)

    def can_edit(self, user: User):
        return user.id in self.chat.administrators or user.is_admin

class Timeout(db.Entity):
    id = PrimaryKey(int, auto=True)
    captcha = Optional(Captcha, column="captcha")
    token = Optional(VerificationToken, column="token")
    seconds = Required(int)
    start_date = Required(datetime, default=datetime.now)
    expiration_date = Required(datetime)
    is_valid = Required(bool, default=True)

    DEFAULT_SECONDS = 60
    SCHEDULER = AsyncIOScheduler()

    @staticmethod
    def start_scheduler():
        logging.warning('Starting timeout scheduler...')

        Timeout.SCHEDULER.start()

    def __init__(self, *args, **kwargs):
        if 'seconds' in kwargs:
            kwargs['expiration_date'] = datetime.now() + timedelta(seconds=kwargs['seconds'])

        super().__init__(*args, **kwargs)

    @property
    def has_expired(self) -> bool:
        return datetime.now() > self.expiration_date

    @db_session
    def invalidate(self):
        timeout = Timeout.get(id=self.id)

        timeout.is_valid = False

    async def expire(self, client: pyrogram.Client):
        if not self.is_valid:
            return

        self.invalidate()
        with db_session:
            timeout = Timeout.get(id=self.id)
            captcha = timeout.captcha
            token = captcha.token if captcha else timeout.token

            if not token:
                return

            if not captcha:
                captcha = token.captcha

            if captcha and captcha.status != CaptchaStatus.WAITING:
                return

            if captcha:
                with db_session:
                    captcha.current.status = CaptchaStatus.LOST

            chat = token.chat
            user = token.user
            should_unban = False
            keyboard = None

            try:
                member = await client.get_chat_member(chat_id=chat.id, user_id=user.id)

                if not member.is_member:
                    await client.delete_messages(chat_id=chat.id, message_ids=token.message_id)
                    return
                elif not member.restricted_by:
                    return
            except FloodWait as e:
                raise e
            except:
                await client.delete_messages(chat_id=chat.id, message_ids=token.message_id)

            delay = chat.get_setting('captcha_delay') if chat else None

            if delay is None:
                delay = Captcha.DEFAULT_DELAY

            delay = int(delay)

            localizator = chat or user

            if delay > 30:
                time_str = localizator.get_message('in') + ' ' + timeutils.string(delay, localizator, 100)
            else:
                time_str = localizator.get_message('when_they_rejoin')

            if chat:
                group_text = chat.get_message('timeout_expired_group', time=time_str, mention=user.mention)
            else:
                group_text = user.get_message('timeout_expired_group', time=time_str, mention=user.mention)

            if token and token.destination == TokenDestination.PRIVATE:
                if captcha:
                    await client.delete_messages(chat_id=user.id, message_ids=captcha.message_id)

                if delay > 30:
                    time_str = user.get_message('in') + ' ' + timeutils.string(delay, user, 100)
                else:
                    time_str = user.get_message('when_you_rejoin')

                private_text = user.get_message('timeout_expired_private', mention=chat.mention, time=time_str)

                await client.send_message(chat_id=user.id, text=private_text, disable_web_page_preview=True)

            if chat and chat.has_permissions:
                keyboard = unban.unban_keyboard(chat, user)

                msg = await client.kick_chat_member(chat_id=chat.id,
                                                    user_id=user.id,
                                                    until_date=delay if delay >= 30 else 30)

                if isinstance(msg, types.Message):
                    try:
                        await msg.delete()
                    except RPCError:
                        pass

                if delay < 30:
                    should_unban = True
                    keyboard = None

            if chat:
                await client.delete_messages(chat_id=chat.id, message_ids=token.message_id)

                await client.send_message(chat.id, group_text, reply_to_message_id=token.reply_to_message_id,
                                          disable_web_page_preview=True, reply_markup=keyboard)

            if should_unban:
                await client.unban_chat_member(chat_id=chat.id,
                                               user_id=user.id)

    async def start(self, client: pyrogram.Client) -> Job:
        return self.SCHEDULER.add_job(self.expire, 'date', run_date=self.expiration_date, args=[client])


def setup():
    logging.warning('Initializing DB...')

    db.bind(**config.DB_CON)
    db.generate_mapping(create_tables=True)

    logging.warning('DB Initialized!')

    config.VERSION = Changelog.get_latest_version() or 1.0
    Timeout.start_scheduler()

    logging.warning(f'Bot Version: {config.VERSION}')
