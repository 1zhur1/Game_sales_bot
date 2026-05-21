"""
🎮 WTF_Steam — утилиты форматирования.

Единый стиль сообщений: современный, игровой, премиальный.
Все тексты бота проходят через этот модуль.
"""

import html
from typing import Optional


def fmt(text: str) -> str:
    """HTML-escape для безопасности."""
    return html.escape(text)


def generate_short_description(title: str) -> str:
    """Генерирует короткое описание игры на основе названия."""
    return f"Скидка на игру: {title}. Успей купить по выгодной цене!"


def format_game(game, index: int, total: int) -> str:
    """
    💎 Премиальная карточка игры.

    Для платных:
    🎮 Название
    💾 Жанры
    ⭐ Рейтинг
    💸 -75%  →  ️499₽
    🕒 Скидка заканчивается: ...
    🔗 Ссылка

    Для бесплатных:
    🎮 Название
    🎁 ЗАБЕРИ БЕСПЛАТНО
    🏪 Steam/Epic
    🔗 Ссылка
    """
    title = fmt(game.title)

    # ─── Бесплатная игра ─────────────────────────
    if game.is_free:
        return (
            f"🎮 <b>{title}</b>\n\n"
            f"🎁 <b>ЗАБЕРИ БЕСПЛАТНО</b>\n"
            f"🏪 {game.store}\n"
            f"⭐ {game.rating_text}\n\n"
            f'🔗 <a href="{game.url}">Забрать игру</a>\n\n'
            f"📄 {index + 1}/{total}"
        )

    # ─── Скидочная игра ──────────────────────────
    discount = game.discount_percent
    original = game.original_price
    discounted = game.discounted_price
    rating = game.rating_percent
    rating_text = game.rating_text

    # Оценка выгодности
    deal_rating = ""
    if discount >= 75:
        deal_rating = "🔥🔥🔥 БОМБА"
    elif discount >= 50:
        deal_rating = "🔥🔥 Отлично"
    elif discount >= 30:
        deal_rating = "🔥 Хорошая скидка"
    elif discount > 0:
        deal_rating = "💸 Неплохо"

    return (
        f"🎮 <b>{title}</b>\n\n"
        f"🏷 <s>{original}</s>\n"
        f"💸 <b>{discounted}</b>\n"
        f"🔥 <b>-{discount}%</b>  ·  {deal_rating}\n"
        f"⭐ {rating}%  ·  {rating_text}\n"
        f"🏪 {game.store}\n\n"
        f'🔗 <a href="{game.url}">Открыть в магазине</a>\n\n'
        f"📄 {index + 1}/{total}"
    )


def format_deal_from_cache(deal: dict, index: int, total: int) -> str:
    """Форматирует сделку из кэша БД (словарь)."""
    title = fmt(deal["title"])
    store = deal["store"]
    discount = deal["discount_percent"]
    is_free = deal["is_free"]
    price = deal.get("price", 0)
    original = deal.get("original_price", 0)
    url = deal.get("url", "")

    if is_free:
        return (
            f"🎮 <b>{title}</b>\n\n"
            f"🎁 <b>ЗАБЕРИ БЕСПЛАТНО</b>\n"
            f"🏪 {store}\n\n"
            f'🔗 <a href="{url}">Забрать игру</a>\n\n'
            f"📄 {index + 1}/{total}"
        )

    # Оценка выгодности
    deal_rating = ""
    if discount >= 75:
        deal_rating = "🔥🔥🔥 БОМБА"
    elif discount >= 50:
        deal_rating = "🔥🔥 Отлично"
    elif discount >= 30:
        deal_rating = "🔥 Хорошая скидка"
    elif discount > 0:
        deal_rating = "💸 Неплохо"

    text = f"🎮 <b>{title}</b>\n\n"

    if original > 0:
        text += f"🏷 <s>{original:.0f}₽</s>\n"

    if price > 0:
        text += f"💸 <b>{price:.0f}₽</b>\n"

    text += f"🔥 <b>-{discount}%</b>  ·  {deal_rating}\n"
    text += f"🏪 {store}\n\n"
    text += f'🔗 <a href="{url}">Открыть в магазине</a>\n\n'
    text += f"📄 {index + 1}/{total}"

    return text


# ═══════════════════════════════════════════════════════════════
# 🏠 СООБЩЕНИЯ ДЛЯ ЭКРАНОВ
# ═══════════════════════════════════════════════════════════════

def main_menu_text() -> str:
    return (
        "🎮 <b>WTF_Steam</b>\n\n"
        "Твой игровой центр. Всё в одном месте:\n"
        "скидки, халява, подборки и уведомления.\n\n"
        "Выбери раздел: 👇"
    )


def store_menu_text() -> str:
    return (
        "🎮 <b>Магазины</b>\n\n"
        "Смотри актуальные скидки и халяву\n"
        "в Steam и Epic Games.\n\n"
        "Выбери магазин: 👇"
    )


def free_menu_text() -> str:
    return (
        "🎁 <b>Халява</b>\n\n"
        "Бесплатные игры прямо сейчас.\n"
        "Забирай, пока не закончилось!\n\n"
        "Выбери платформу: 👇"
    )


def top_menu_text() -> str:
    return (
        "🔥 <b>Топ</b>\n\n"
        "Лучшие предложения, популярное\n"
        "и свежие новинки.\n\n"
        "Выбери, что интересно: 👇"
    )


def my_menu_text() -> str:
    return (
        "❤️ <b>Моё</b>\n\n"
        "Твои подписки, избранное\n"
        "и отслеживаемые игры.\n\n"
        "Выбери раздел: 👇"
    )


def settings_menu_text(settings: dict) -> str:
    notif = "✅ Включены" if settings.get("notifications_enabled", True) else "❌ Отключены"
    discount = settings.get("min_discount_percent", 0)
    return (
        "⚙️ <b>Настройки</b>\n\n"
        "Настрой бота под себя.\n\n"
        f"🔔 Уведомления: {notif}\n"
        f"📉 Мин. скидка: {discount}%\n\n"
        "<i>Уведомления приходят, только если\n"
        "скидка >= указанного процента.</i>"
    )


def subscribe_menu_text() -> str:
    return (
        "🔔 <b>Подписка на игру</b>\n\n"
        "Я буду отслеживать скидки и раздачи\n"
        "для выбранной игры и пришлю\n"
        "уведомление, когда цена упадёт.\n\n"
        "Просто введи название! 👇"
    )


def empty_list_text(section: str, hint: str = "") -> str:
    texts = {
        "subscriptions": (
            "📌 <b>Нет активных подписок</b>\n\n"
            "Найди игру в магазинах и подпишись\n"
            "на скидки, чтобы ничего не пропустить."
        ),
        "favorites": (
            "⭐ <b>Избранное пусто</b>\n\n"
            "Добавляй игры в избранное,\n"
            "чтобы не потерять их."
        ),
        "filters": (
            "😕 <b>Ничего не найдено</b>\n\n"
            "Измени фильтры или попробуй\n"
            "другую категорию."
        ),
    }
    return texts.get(section, f"📭 <b>{section}</b>")