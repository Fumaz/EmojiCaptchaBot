from plate import Plate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from util import config

plate = Plate(root=config.LANGUAGES_DIR)


def get_message(message_name: str, language_name: str = 'en_US', **kwargs):
    try:
        return plate(message_name, language_name, **kwargs)
    except ValueError:
        return plate(message_name, 'en_US', **kwargs)


def create_keyboard(is_group: bool, back: InlineKeyboardButton, settings=None) -> InlineKeyboardMarkup:
    keyboard = [[]]

    for lang in plate.locales:
        if len(keyboard[-1]) >= 3:
            keyboard.append([])

        flag = plate('flag', lang)
        keyboard[-1].append(
            InlineKeyboardButton(flag, callback_data=f'language_{f"g_{settings.id}" if is_group else "p"}_{lang}')
        )

    keyboard.append([back])

    return InlineKeyboardMarkup(keyboard)


def create_message_data(user, chat=None, settings=None) -> dict:
    is_group = chat is not None
    localizator = chat or user

    msg_args = {}
    if is_group:
        msg_args['mention'] = chat.mention

    msg = localizator.get_message('language_select_' + ('group' if is_group else 'private'), **msg_args)
    back = InlineKeyboardButton(localizator.get_message('back'),
                                callback_data=f'settings_{settings.id}' if settings else 'main_menu')

    keyboard = create_keyboard(is_group, settings=settings, back=back)

    return dict(text=msg, reply_markup=keyboard)


def get_nearest(language: str) -> str:
    if not language or not isinstance(language, str):
        return 'en_US'

    if language.startswith('it'):
        return 'it_IT'

    return 'en_US'
