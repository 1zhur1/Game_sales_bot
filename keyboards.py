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

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"{prefix}_{index - 1}"
            ),

            InlineKeyboardButton(
                f"{index + 1}/{total}",
                callback_data="ignore"
            ),

            InlineKeyboardButton(
                "➡️",
                callback_data=f"{prefix}_{index + 1}"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 Главное меню",
                callback_data="main_menu"
            )
        ]
    ])