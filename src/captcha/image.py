import json
import logging
import random
from functools import lru_cache
from typing import Union, Tuple

from PIL import Image

from util import config

LOCATIONS = {}
LOCATIONS_FILE = config.ASSETS_DIR + 'locations.json'


def load_locations():
    global LOCATIONS

    logging.warning('Loading locations...')

    with open(LOCATIONS_FILE, 'r') as file:
        LOCATIONS = json.load(file)

    logging.warning(f'Loaded {len(LOCATIONS)} locations!')


@lru_cache(maxsize=None)
def from_resolution(width: int, height: int):
    return LOCATIONS[f'{width}x{height}']


def apply_watermark(background: Image.Image, watermark: Union[Image.Image, str],
                    size: Tuple[int], location: Tuple[int]) -> Image.Image:
    if not isinstance(watermark, Image.Image):
        watermark = Image.open(watermark)

    if watermark.mode != 'RGBA':
        watermark = watermark.convert('RGBA')

    watermark = watermark.resize(size, Image.ANTIALIAS)

    background.paste(watermark, location, watermark)
    watermark.close()

    return background


def overlay(background: Image.Image, over: Union[Image.Image, str], size: Tuple[int],
            location: Tuple[int], rotation: int) -> Image.Image:
    if not isinstance(over, Image.Image):
        over = Image.open(over)

    if over.mode != 'RGBA':
        over = over.convert('RGBA')

    over = over.resize(size, Image.ANTIALIAS).rotate(rotation, Image.BICUBIC, expand=True)

    background.paste(over, location, over)
    over.close()

    return background


def create(background: str, watermark: str, emojis: Tuple[str]) -> Image.Image:
    background = Image.open(config.BACKGROUNDS_DIR + background)

    if background.mode != 'RGBA':
        background = background.convert('RGBA')

    settings = from_resolution(*background.size)
    emoji_sizes = settings['emoji-sizes']
    locations = settings['locations']
    rotations = random.sample(range(0, 360, 15), k=len(emojis))
    watermark_size = settings['watermark-size']
    watermark_location = random.choice(settings['watermark-locations'])
    i = 0

    h = random.randint(emoji_sizes[0], emoji_sizes[1])
    width, height = (h, h)

    apply_watermark(background, config.WATERMARKS_DIR + watermark, watermark_size, watermark_location)

    for emoji in emojis:
        if len(locations) < i + 1:
            break

        location = locations[i].copy()
        rotation = rotations[i]

        background = overlay(background=background,
                             over=config.EMOJIS_DIR + emoji,
                             size=tuple([width, height]),
                             location=location,
                             rotation=rotation)

        i += 1

    return background
