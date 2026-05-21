BANNED = [
    "hentai",
    "sex",
    "futa",
    "waifu",
    "furry",
    "nsfw",
    "clicker",
]


def is_low_quality_game(title: str):

    title = title.lower()

    for word in BANNED:
        if word in title:
            return True

    return False