import html


def generate_short_description(title):

    texts = [
        f"{title} — одна из лучших игр со скидкой.",
        f"{title} получила множество положительных отзывов.",
        f"{title} — популярная игра с высоким рейтингом.",
    ]

    return texts[hash(title) % len(texts)]


def format_game(game, index, total):

    title = html.escape(game.title)
    desc = html.escape(game.description)

    if game.is_free:

        return (
            f"🎮 <b>{title}</b>\n\n"
            f"🎁 <b>БЕСПЛАТНО</b>\n"
            f"🏪 {game.store}\n"
            f"⭐ {game.rating_text}\n\n"
            f"📝 {desc}\n\n"
            f'🔗 <a href="{game.url}">Забрать игру</a>\n\n'
            f"📄 {index + 1}/{total}"
        )

    return (
        f"🎮 <b>{title}</b>\n\n"
        f"🏷 <s>{game.original_price}</s>\n"
        f"💸 <b>{game.discounted_price}</b>\n"
        f"🔥 Скидка: -{game.discount_percent}%\n"
        f"⭐ {game.rating_percent}%\n"
        f"🏪 {game.store}\n\n"
        f"📝 {desc}\n\n"
        f'🔗 <a href="{game.url}">Открыть магазин</a>\n\n'
        f"📄 {index + 1}/{total}"
    )