from plate import emojipedia


def to_bool(string: str) -> bool:
    return string and string.lower() in ('true', 'yes', 't')


def to_emoji(b: bool) -> str:
    return emojipedia.CHECK_MARK_BUTTON if b else emojipedia.CROSS_MARK
