import time
import aiohttp

from models import GameDeal
from filters import is_low_quality_game
from utils import generate_short_description

CACHE = {
    "epic_free": {
        "timestamp": 0,
        "data": []
    },
    "epic_deals": {
        "timestamp": 0,
        "data": []
    }
}

CACHE_TTL = 3600

EPIC_URL = (
    "https://store-site-backend-static-ipv4.ak.epicgames.com/"
    "freeGamesPromotions"
)


def get_cache(key):

    item = CACHE.get(key)

    if not item:
        return None

    if time.time() - item["timestamp"] > CACHE_TTL:
        return None

    return item["data"]


def set_cache(key, data):

    CACHE[key] = {
        "timestamp": time.time(),
        "data": data
    }


async def get_epic_free_games():

    cached = get_cache("epic_free")

    if cached:
        return cached

    games = []

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                EPIC_URL,
                timeout=20
            ) as response:

                data = await response.json()

        elements = (
            data["data"]["Catalog"]
            ["searchStore"]["elements"]
        )

        for item in elements:

            try:

                title = item.get("title")

                if is_low_quality_game(title):
                    continue

                promotions = item.get("promotions")

                if not promotions:
                    continue

                promotional = promotions.get(
                    "promotionalOffers"
                )

                if not promotional:
                    continue

                discount_price = (
                    item["price"]["totalPrice"]
                    ["discountPrice"]
                )

                if discount_price != 0:
                    continue

                image = None

                for img in item.get("keyImages", []):

                    if img.get("type") == "OfferImageWide":
                        image = img.get("url")
                        break

                slug = item.get("productSlug")

                if not slug:
                    url_mappings = item.get("urlMappings", [])
                    if url_mappings:
                        slug = url_mappings[0].get("pageSlug", "")

                if not slug:
                    continue

                game = GameDeal(
                    title=title,
                    original_price="—",
                    discounted_price="БЕСПЛАТНО",
                    discount_percent=100,
                    rating_percent=90,
                    rating_text="Популярная игра",
                    description=generate_short_description(
                        title
                    ),
                    url=f"https://store.epicgames.com/p/{slug}",
                    store="Epic Games",
                    image=image,
                    is_free=True
                )

                games.append(game)

            except:
                continue

        set_cache("epic_free", games)

        return games

    except:
        return []


async def get_epic_deals():

    cached = get_cache("epic_deals")

    if cached:
        return cached

    games = []

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                EPIC_URL,
                timeout=20
            ) as response:

                data = await response.json()

        elements = (
            data["data"]["Catalog"]
            ["searchStore"]["elements"]
        )

        for item in elements:

            try:

                title = item.get("title")

                if is_low_quality_game(title):
                    continue

                price_info = item.get("price", {}).get("totalPrice", {})
                original_price_cents = price_info.get("originalPrice", 0)
                discount_price_cents = price_info.get("discountPrice", 0)

                # Пропускаем бесплатные (они уже в get_epic_free_games)
                if discount_price_cents <= 0:
                    continue

                # Пропускаем если нет скидки
                if discount_price_cents >= original_price_cents:
                    continue

                # Вычисляем процент скидки
                if original_price_cents > 0:
                    discount_percent = int(
                        (1 - discount_price_cents / original_price_cents) * 100
                    )
                else:
                    discount_percent = 0

                image = None

                for img in item.get("keyImages", []):

                    if img.get("type") == "OfferImageWide":
                        image = img.get("url")
                        break

                slug = item.get("productSlug")

                if not slug:
                    url_mappings = item.get("urlMappings", [])
                    if url_mappings:
                        slug = url_mappings[0].get("pageSlug", "")

                if not slug:
                    continue

                # Форматируем цены
                original_price = f"{original_price_cents / 100:.2f}$"
                discounted_price = f"{discount_price_cents / 100:.2f}$"

                ame = GameDeal(
                    title=title,
                    original_price=original_price,
                    discounted_price=discounted_price,
                    discount_percent=discount_percent,
                    rating_percent=85,
                    rating_text="Высокий рейтинг",
                    description=generate_short_description(
                        title
                    ),
                    url=f"https://store.epicgames.com/p/{slug}",
                    store="Epic Games",
                    image=image,
                    is_free=False,
                )

                games.append(game)

            except:
                continue

        set_cache("epic_deals", games)

        return games

    except:
        return []