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


def format_deal_from_cache(deal: dict, index: int, total: int) -> str:
    """Форматирование сделки из кэша БД."""
    title = html.escape(deal["title"])
    store = deal["store"]
    discount = deal["discount_percent"]
    is_free = deal["is_free"]
    price = deal.get("price", 0)
    original = deal.get("original_price", 0)

    if is_free:
        return (
            f"🎮 <b>{title}</b>\n\n"
            f"🎁 <b>БЕСПЛАТНО</b>\n"
            f"🏪 {store}\n\n"
            f'🔗 <a href="{deal.get("url", "")}">Забрать игру</a>\n\n'
            f"📄 {index + 1}/{total}"
        )

    text = f"🎮 <b>{title}</b>\n\n"

    if original > 0:
        text += f"🏷 <s>{original:.0f}₽</s>\n"

    if price > 0:
        text += f"💸 <b>{price:.0f}₽</b>\n"

    text += f"🔥 Скидка: -{discount}%\n"
    text += f"🏪 {store}\n\n"
    text += f'🔗 <a href="{deal.get("url", "")}">Открыть магазин</a>\n\n'
    text += f"📄 {index + 1}/{total}"

    return text