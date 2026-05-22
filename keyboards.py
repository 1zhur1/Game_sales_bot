"""
🎮 GameHub — UI/UX клавиатуры для игрового бота.

Единый стиль: минималистично, современно, игровой vibe.
Все callback_data используют префиксы.
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from database import make_deal_id


# ═══════════════════════════════════════════════════════════════
# 🏠 ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════

def main_menu():
    """
    Компактное главное меню — 5 основных разделов.
    Максимум одна строка на категорию, но выглядит как 2x2 + 1 снизу.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Магазины", callback_data="store_menu"),
            InlineKeyboardButton("🔥 Топ", callback_data="top_menu"),
        ],
        [
            InlineKeyboardButton("❤️ Моё", callback_data="my_menu"),
            InlineKeyboardButton("🎯 Фильтры", callback_data="filters_menu"),
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings_menu"),
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# 🎮 МАГАЗИНЫ
# ═══════════════════════════════════════════════════════════════

def store_menu_keyboard():
    """Подменю магазинов: Steam, Epic, Бесплатные, Назад."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔥 Steam Sale", callback_data="steam_deals_0"),
            InlineKeyboardButton("🔥 Epic Sale", callback_data="epic_deals_0"),
        ],
        [
            InlineKeyboardButton("🎁 Халява", callback_data="free_menu"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu"),
        ],
    ])


def free_menu_keyboard():
    """Бесплатные игры: Steam / Epic / Назад в магазины."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 Epic Free", callback_data="epic_free_0"),
        ],
        [
            InlineKeyboardButton("🎁 Steam Free", callback_data="steam_free_0"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="store_menu"),
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# 🔥 ТОП / РЕКОМЕНДАЦИИ
# ═══════════════════════════════════════════════════════════════

def top_menu_keyboard():
    """Раздел топ-рекомендаций."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔥 Для вас", callback_data="recommendations"),
        ],
        [
            InlineKeyboardButton("📈 Популярное", callback_data="popular"),
        ],
        [
            InlineKeyboardButton("🆕 Новинки", callback_data="new_releases"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu"),
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# ❤️ МОЁ
# ═══════════════════════════════════════════════════════════════

def my_menu_keyboard():
    """Раздел пользователя: подписки, избранное."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📌 Подписки", callback_data="my_subscriptions_0"),
        ],
        [
            InlineKeyboardButton("⭐ Избранное", callback_data="my_favorites_0"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu"),
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# 📄 НАВИГАЦИЯ ПО СПИСКАМ (универсальная)
# ═══════════════════════════════════════════════════════════════

def nav_keyboard(prefix: str, index: int, total: int):
    """
    Универсальная навигация для листания списков.
    ⬅️  1/15  ➡️
         🏠 Главное меню
    """
    buttons = []

    if total > 1:
        nav_row = []
        if index > 0:
            nav_row.append(
                InlineKeyboardButton("⬅️", callback_data=f"{prefix}_{index - 1}")
            )
        nav_row.append(
            InlineKeyboardButton(f"{index + 1}/{total}", callback_data="ignore")
        )
        if index < total - 1:
            nav_row.append(
                InlineKeyboardButton("➡️", callback_data=f"{prefix}_{index + 1}")
            )
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(buttons)


def empty_nav_keyboard():
    """Когда ничего нет — только кнопка назад."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# 🔔 ПОДПИСКИ
# ═══════════════════════════════════════════════════════════════

def subscribe_menu_keyboard():
    """Меню подписки — поиск игры / назад."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Найти игру", callback_data="subscribe_search"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="my_menu"),
        ],
    ])


def game_selection_keyboard(games: list[dict], prefix: str = "sub_choose"):
    """Выбор игры из результатов поиска (до 5 шт, компактно)."""
    buttons = []
    for i, game in enumerate(games):
        title = game["title"]
        store = game["store"]
        if len(title) > 36:
            title = title[:33] + "..."
        buttons.append([
            InlineKeyboardButton(
                f"🎮 {title}  ·  {store}",
                callback_data=f"{prefix}_{i}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔍 Другой поиск", callback_data="subscribe_search"),
    ])
    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="my_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def _make_game_callback(prefix: str, game_title: str, store: str) -> str:
    """
    Создаёт callback_data для действий с игрой, используя хэш deal_id.
    Telegram callback_data <= 64 байт, поэтому используем сокращённый идентификатор.
    """
    deal_id = make_deal_id(store, game_title)
    # Берём первые 55 символов от deal_id (оставляем место под префикс)
    short_id = deal_id[:55]
    return f"{prefix}{short_id}"


def _parse_game_callback(data: str, prefix: str) -> tuple:
    """
    Разбирает callback_data обратно в game_title и store.
    Возвращает (game_title, store) или None.
    """
    if not data.startswith(prefix):
        return None
    short_id = data[len(prefix):]
    # Восстанавливаем: формат store:title
    if ":" in short_id:
        store_part, title_part = short_id.split(":", 1)
        # Нормализуем название магазина
        store_lower = store_part.lower().strip()
        if store_lower == "steam":
            store = "Steam"
        elif "epic" in store_lower:
            store = "Epic Games"
        else:
            store = store_part
        return (title_part, store)
    return None


def subscription_action_keyboard(
    game_title: str,
    store: str,
    is_subscribed: bool = False,
    is_favorite: bool = False,
):
    """Действия над конкретной игрой: подписка / избранное."""
    buttons = []

    if is_subscribed:
        buttons.append([
            InlineKeyboardButton(
                "🔔 ✅ Подписан · Отписаться",
                callback_data=_make_game_callback("unsub_", game_title, store),
            ),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                "🔔 Подписаться на скидки",
                callback_data=_make_game_callback("sub_confirm_", game_title, store),
            ),
        ])

    fav_label = "⭐ В избранное" if not is_favorite else "⭐ ✅ В избранном"
    buttons.append([
        InlineKeyboardButton(fav_label, callback_data=_make_game_callback("fav_", game_title, store)),
    ])

    buttons.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def my_subscriptions_keyboard(subscriptions: list[dict], page: int = 0, items_per_page: int = 5):
    """Список подписок с навигацией."""
    buttons = []
    start = page * items_per_page
    end = start + items_per_page
    page_items = subscriptions[start:end]

    for sub in page_items:
        title = sub["game_title"]
        store = sub["store"]
        if len(title) > 32:
            title = title[:29] + "..."
        buttons.append([
            InlineKeyboardButton(
                f"❌ {title}  ·  {store}",
                callback_data=_make_game_callback("unsub_", sub["game_title"], store),
            ),
        ])

    # Навигация
    total_pages = max(1, (len(subscriptions) + items_per_page - 1) // items_per_page)
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton("⬅️", callback_data=f"my_subscriptions_{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ignore")
    )
    if end < len(subscriptions):
        nav_row.append(
            InlineKeyboardButton("➡️", callback_data=f"my_subscriptions_{page + 1}")
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def my_favorites_keyboard(favorites: list[dict], page: int = 0, items_per_page: int = 5):
    """Список избранного с навигацией."""
    buttons = []
    start = page * items_per_page
    end = start + items_per_page
    page_items = favorites[start:end]

    for fav in page_items:
        title = fav["game_title"]
        store = fav["store"]
        if len(title) > 32:
            title = title[:29] + "..."
        buttons.append([
            InlineKeyboardButton(
                f"⭐ {title}  ·  {store}",
                callback_data=_make_game_callback("game_info_", fav["game_title"], store),
            ),
        ])

    total_pages = max(1, (len(favorites) + items_per_page - 1) // items_per_page)
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton("⬅️", callback_data=f"my_favorites_{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ignore")
    )
    if end < len(favorites):
        nav_row.append(
            InlineKeyboardButton("➡️", callback_data=f"my_favorites_{page + 1}")
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


# ═══════════════════════════════════════════════════════════════
# ⚙️ НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════

def settings_keyboard(user_settings: dict):
    """Настройки пользователя."""
    notif_status = "✅ Вкл" if user_settings.get("notifications_enabled", True) else "❌ Выкл"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"🔔 Уведомления: {notif_status}",
                callback_data="settings_toggle_notif",
            ),
        ],
        [
            InlineKeyboardButton(
                "🎯 Фильтры уведомлений",
                callback_data="settings_notif_filters",
            ),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu"),
        ],
    ])


def discount_filter_keyboard_v1(current: int = 0):
    """Выбор минимальной скидки (старая версия, для настроек)."""
    values = [0, 10, 20, 30, 50, 70, 80, 90]
    buttons = []
    row = []
    for v in values:
        marker = "✅" if v == current else f"{v}%"
        row.append(
            InlineKeyboardButton(marker, callback_data=f"set_min_discount_{v}")
        )
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="settings_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def notif_filters_main_keyboard(notif_filters: dict):
    """Главное меню фильтров уведомлений."""
    genres = notif_filters.get("selected_genres", [])
    genres_text = f"{len(genres)} жанров" if genres else "Все"
    md = notif_filters.get("min_discount", 0)
    md_text = f"{md}%" if md > 0 else "Любая"
    pf = notif_filters.get("platform", "all")
    plat_names = {"all": "Все", "steam": "Steam", "epic games": "Epic Games"}
    ft = notif_filters.get("filter_type", "all")
    ft_names = {"all": "Всё", "discounts": "Скидки", "free": "Халява"}
    rf = notif_filters.get("rating_filter", 0)
    rf_text = f"{rf}%+" if rf > 0 else "Любой"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎭 Жанры: {genres_text}", callback_data="nf_genres")],
        [InlineKeyboardButton(f"💸 Мин. скидка: {md_text}", callback_data="nf_discount")],
        [InlineKeyboardButton(f"🖥 Платформа: {plat_names.get(pf, pf)}", callback_data="nf_platform")],
        [InlineKeyboardButton(f"🎯 Тип: {ft_names.get(ft, ft)}", callback_data="nf_type")],
        [InlineKeyboardButton(f"⭐ Рейтинг: {rf_text}", callback_data="nf_rating")],
        [InlineKeyboardButton("🧹 Сбросить", callback_data="nf_reset")],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings_menu")],
    ])


# ═══════════════════════════════════════════════════════════════
# 🎯 СИСТЕМА ФИЛЬТРОВ
# ═══════════════════════════════════════════════════════════════

def filters_main_menu_keyboard():
    """Главное меню фильтров."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎭 Жанры", callback_data="filters_genres"),
            InlineKeyboardButton("💸 Скидка", callback_data="filters_discount"),
        ],
        [
            InlineKeyboardButton("💰 Цена", callback_data="filters_price"),
            InlineKeyboardButton("⭐ Рейтинг", callback_data="filters_rating"),
        ],
        [
            InlineKeyboardButton("🖥 Платформа", callback_data="filters_platform"),
            InlineKeyboardButton("🎯 Тип", callback_data="filters_type"),
        ],
        [
            InlineKeyboardButton("📊 Сортировка", callback_data="filters_sort"),
        ],
        [
            InlineKeyboardButton("🧹 Сбросить фильтры", callback_data="filters_reset"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu"),
        ],
    ])


def genres_keyboard(selected: set):
    """Выбор жанров (мультивыбор)."""
    from services.filter_service import ALL_GENRES

    buttons = []
    row = []
    for genre in ALL_GENRES:
        marker = "✅" if genre in selected else genre
        row.append(
            InlineKeyboardButton(marker, callback_data=f"fgenre_toggle_{genre}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("✅ Готово", callback_data="fgenre_done"),
    ])

    return InlineKeyboardMarkup(buttons)


def discount_filter_keyboard_v2(current: int = 0):
    """Выбор минимальной скидки (для системы фильтров)."""
    values = [0, 10, 25, 50, 75, 90, 100]
    buttons = []
    row = []
    for v in values:
        marker = "✅" if v == current else f"{v}%"
        row.append(
            InlineKeyboardButton(marker, callback_data=f"fset_discount_{v}")
        )
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="filters_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def price_filter_keyboard(current: float = 0):
    """Выбор максимальной цены."""
    values = [0, 1, 5, 10, 20, 50]
    buttons = []
    row = []
    for v in values:
        label = "Любая" if v == 0 else f"${v}"
        marker = "✅" if current == v else label
        row.append(
            InlineKeyboardButton(marker, callback_data=f"fset_price_{v}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="filters_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def platform_filter_keyboard(current: str = "all"):
    """Выбор платформы."""
    options = [
        ("all", "Все"),
        ("steam", "Steam"),
        ("epic games", "Epic Games"),
    ]
    buttons = []
    for key, label in options:
        marker = "✅" if current == key else label
        buttons.append([
            InlineKeyboardButton(marker, callback_data=f"fset_platform_{key}"),
        ])

    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="filters_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def filter_type_keyboard(current: str = "all"):
    """Выбор типа контента."""
    options = [
        ("all", "Всё подряд"),
        ("discounts", "Только скидки"),
        ("free", "Только халява"),
    ]
    buttons = []
    for key, label in options:
        marker = "✅" if current == key else label
        buttons.append([
            InlineKeyboardButton(marker, callback_data=f"fset_type_{key}"),
        ])

    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="filters_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def sort_type_keyboard(current: str = "discount"):
    """Выбор сортировки."""
    options = [
        ("discount", "По скидке"),
        ("price", "По цене"),
        ("rating", "По рейтингу"),
        ("title", "По алфавиту"),
        ("popularity", "По популярности"),
    ]
    buttons = []
    for key, label in options:
        marker = "✅" if current == key else label
        buttons.append([
            InlineKeyboardButton(marker, callback_data=f"fset_sort_{key}"),
        ])

    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="filters_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def rating_filter_keyboard(current: int = 0):
    """Выбор минимального рейтинга."""
    values = [0, 50, 70, 80, 90, 95]
    buttons = []
    row = []
    for v in values:
        label = "Любой" if v == 0 else f"{v}%+"
        marker = "✅" if current == v else label
        row.append(
            InlineKeyboardButton(marker, callback_data=f"fset_rating_{v}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="filters_menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def filtered_nav_keyboard(prefix: str, index: int, total: int):
    """
    Навигация для отфильтрованных списков игр.
    ⬅️  4/42  ➡️
         🎯 Фильтры
         🏠 Главное меню
    """
    buttons = []

    if total > 1:
        nav_row = []
        if index > 0:
            nav_row.append(
                InlineKeyboardButton("⬅️", callback_data=f"{prefix}_{index - 1}")
            )
        nav_row.append(
            InlineKeyboardButton(f"{index + 1}/{total}", callback_data="ignore")
        )
        if index < total - 1:
            nav_row.append(
                InlineKeyboardButton("➡️", callback_data=f"{prefix}_{index + 1}")
            )
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🎯 Фильтры", callback_data="filters_menu"),
    ])
    buttons.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
    ])

    return InlineKeyboardMarkup(buttons)