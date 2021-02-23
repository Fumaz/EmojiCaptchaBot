import json
import re

from util import config


def to_bytes(emoji: str) -> bytes:
    return emoji.encode('unicode-escape')


def image_name(u: bytes) -> str:
    bytes_arr = re.split(r'\\U', u.decode('utf-8'), flags=re.IGNORECASE)
    img_name = ""

    for b in bytes_arr:
        if not b:
            continue

        if img_name:
            img_name += '_'

        img_name += b.lstrip('0')

    return img_name


def txt_to_json(file_name: str = 'emojis.txt', output_file: str = 'emojis.json'):
    with open(config.ASSETS_DIR + file_name, 'r') as in_file:
        emojis = in_file.read().split('\n')

        with open(config.ASSETS_DIR + output_file, 'w') as out_file:
            json.dump(emojis, out_file)


def mapped(file_name: str = 'emojis.json', output_file: str = 'mapped.json'):
    with open(config.ASSETS_DIR + file_name, 'r') as in_file:
        emojis = json.load(in_file)

        with open(config.ASSETS_DIR + output_file, 'w') as out_file:
            data = {}

            for emoji in emojis:
                data[emoji] = image_name(to_bytes(emoji))

            json.dump(data, out_file)
