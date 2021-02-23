import json
import logging
import random
from typing import Union

from util import config

EMOJIS = {}
EMOJI_LIST = []
MAP_FILE = config.ASSETS_DIR + 'mapped.json'


def load(file_name: str = MAP_FILE):
    global EMOJIS, EMOJI_LIST

    logging.warning('Loading emojis...')

    with open(file_name, 'r') as file:
        EMOJIS = json.load(file)
        EMOJI_LIST = tuple(EMOJIS.items())

    logging.warning(f'Loaded {len(EMOJIS)} emojis!')


def get_random(amount: int = 1) -> tuple:
    return tuple(random.sample(EMOJI_LIST, k=amount))


def get_random_ext(amount: int = 1) -> tuple:
    values = get_random(amount)
    t = []

    for k, v in values:
        t.append((k, v + '.png'))

    return tuple(t)


def extensions_only(emojis: Union[list, tuple]) -> tuple:
    extensions = []

    for emoji in emojis:
        extensions.append(emoji[1])

    return tuple(extensions)


def emojis_only(total: Union[list, tuple]) -> tuple:
    emojis = []

    for emoji in total:
        emojis.append(emoji[0])

    return tuple(emojis)
