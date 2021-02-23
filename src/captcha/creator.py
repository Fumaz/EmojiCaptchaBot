import random

from PIL import Image

from . import emojis, image

DEFAULT_BACKGROUND = 'default.png'
DEFAULT_WATERMARK = 'default.png'
DEFAULT_CORRECT = 6
DEFAULT_TOTAL = 15


def generate(background: str = DEFAULT_BACKGROUND,
             watermark: str = DEFAULT_WATERMARK,
             correct: int = DEFAULT_CORRECT,
             total: int = DEFAULT_TOTAL) -> (Image.Image, list, list):
    total_list = emojis.get_random_ext(amount=total)
    correct_list = random.sample(total_list, k=correct)

    correct_images = emojis.extensions_only(correct_list)
    total_emojis = emojis.emojis_only(total_list)
    correct_emojis = emojis.emojis_only(correct_list)

    return {'image': image.create(background, watermark, correct_images),
            'total': total_emojis,
            'correct': correct_emojis}


def setup():
    emojis.load()
    image.load_locations()
