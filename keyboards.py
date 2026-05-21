from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🎁 Халява",
                callback_data="free_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "🔥 Скидки",
                callback_data="deals_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "🔔 Подписаться на игру",
                callback_data="subscribe_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "📌 Мои подписки",
                callback_data="my_subscriptions_0"
            )
        ],

        [
            InlineKeyboardButton(
                "⭐ Избранное",
                callback_data="my_favorites_0"
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ Настройки",
                callback_data="settings_menu"
            )
        ]
    ])


def free_menu_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🎁 Epic Free",
                callback_data="epic_free_0"
            )
        ],

        [
            InlineKeyboardButton(
                "🎁 Steam Free",
                callback_data="steam_free_0"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 Назад",
                callback_data="main_menu"
            )
        ]
    ])


def deals_menu_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔥 Steam Deals",
                callback_data="steam_deals_0"
            )
        ],

        [
            InlineKeyboardButton(
                "🔥 Epic Deals",
                callback_data="epic_deals_0"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 Назад",
                callback_data="main_menu"
            )
        ]
    ])


def nav_keyboard(prefix, index, total):

    buttons = []

    if total > 1:
        nav_row = []
        if index > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "⬅️",
                    callback_data=f"{prefix}_{index - 1}"
                )
            )

        nav_row.append(
            InlineKeyboardButton(
                f"{index + 1}/{total}",
                callback_data="ignore"
            )
        )

        if index < total - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "➡️",
                    callback_data=f"{prefix}_{index + 1}"
                )
            )

        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="main_menu"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def empty_nav_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏠 Главное меню",
                callback_data="main_menu"
            )
        ]
    ])


def subscribe_menu_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔍 Ввести название игры",
                callback_data="subscribe_search"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Назад",
                callback_data="main_menu"
            )
        ]
    ])


def game_selection_keyboard(games: list[dict], prefix: str = "sub_choose"):

    buttons = []
    for i, game in enumerate(games):
        title = game["title"]
        store = game["store"]
        # Обрезаем длинные названия
        if len(title) > 40:
            title = title[:37] + "..."
        buttons.append([
            InlineKeyboardButton(
                f"{title} ({store})",
                callback_data=f"{prefix}_{i}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔍 Найти другую игру",
            callback_data="subscribe_search"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="main_menu"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def subscription_action_keyboard(game_title: str, store: str, is_subscribed: bool = False,
                                  is_favorite: bool = False):

    buttons = []

    if is_subscribed:
        buttons.append([
            InlineKeyboardButton(
                "❌ Отписаться",
                callback_data=f"unsub_{game_title[:30]}|{store}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                "🔔 Подписаться",
                callback_data=f"sub_confirm_{game_title[:30]}|{store}"
            )
        ])

    fav_text = "⭐ В избранное" if not is_favorite else "✅ В избранном"
    buttons.append([
        InlineKeyboardButton(
            fav_text,
            callback_data=f"fav_{game_title[:30]}|{store}"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="main_menu"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def my_subscriptions_keyboard(subscriptions: list[dict], page: int = 0, items_per_page: int = 5):

    buttons = []
    start = page * items_per_page
    end = start + items_per_page
    page_items = subscriptions[start:end]

    for sub in page_items:
        title = sub["game_title"]
        store = sub["store"]
        if len(title) > 35:
            title = title[:32] + "..."
        buttons.append([
            InlineKeyboardButton(
                f"❌ {title} ({store})",
                callback_data=f"unsub_{sub['game_title'][:30]}|{store}"
            )
        ])

    nav_row = []
    total_pages = max(1, (len(subscriptions) + items_per_page - 1) // items_per_page)

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
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(buttons)


def my_favorites_keyboard(favorites: list[dict], page: int = 0, items_per_page: int = 5):

    buttons = []
    start = page * items_per_page
    end = start + items_per_page
    page_items = favorites[start:end]

    for fav in page_items:
        title = fav["game_title"]
        store = fav["store"]
        if len(title) > 35:
            title = title[:32] + "..."
        buttons.append([
            InlineKeyboardButton(
                f"⭐ {title} ({store})",
                callback_data=f"game_info_{fav['game_title'][:30]}|{store}"
            )
        ])

    nav_row = []
    total_pages = max(1, (len(favorites) + items_per_page - 1) // items_per_page)

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
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(buttons)


def settings_keyboard(user_settings: dict):

    notif_status = "✅ Вкл" if user_settings.get("notifications_enabled", True) else "❌ Выкл"
    min_discount = user_settings.get("min_discount_percent", 0)

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"🔔 Уведомления: {notif_status}",
                callback_data="settings_toggle_notif"
            )
        ],
        [
            InlineKeyboardButton(
                f"📉 Мин. скидка: {min_discount}%",
                callback_data="settings_min_discount"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Главное меню",
                callback_data="main_menu"
            )
        ]
    ])


def discount_filter_keyboard(current: int = 0):

    values = [0, 10, 20, 30, 50, 70, 80, 90]

    buttons = []
    row = []
    for v in values:
        marker = "✅" if v == current else f"{v}%"
        row.append(
            InlineKeyboardButton(
                marker,
                callback_data=f"set_min_discount_{v}"
            )
        )
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🏠 Назад", callback_data="settings_menu")
    ])

    return InlineKeyboardMarkup(buttons)