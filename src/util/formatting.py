from . import config

BASE_URL = f"https://t.me/{config.BOT_USERNAME}"
DEEP_LINK_URL = f"{BASE_URL}?start="
DEEP_LINK_GROUP_URL = f"{BASE_URL}?startgroup="
HTML_LINK = "<a href='{url}'>{text}</a>"

INVISIBLE_CHAR = '⠀'


def deeplink(path: str) -> str:
    return DEEP_LINK_URL + path


def deepgroup(path: str) -> str:
    return DEEP_LINK_GROUP_URL + path


def html_link(url: str, text: str) -> str:
    return HTML_LINK.format(url=url, text=text)


def invisible_link(url: str) -> str:
    return html_link(url, INVISIBLE_CHAR)
