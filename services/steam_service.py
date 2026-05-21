import time
import aiohttp

from models import GameDeal
from filters import is_low_quality_game
from utils import generate_short_description

CACHE = {
    "steam_deals": {
        "timestamp": 0,
        "data": []
    },
    "steam_free": {
        "timestamp": 0,
        "data": []
    }
}

CACHE_TTL = 3600

CHEAPSHARK_URL = (
    "https://www.cheapshark.com/api/1.0/deals"
    "?storeID=1&pageSize=500"
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


async def get_steam_deals():

    cached = get_cache("steam_deals")

    if cached:
        return cached

    games = []

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                CHEAPSHARK_URL,
                timeout=20
            ) as response:

                data = await response.json()

        for item in data:

            try:

                title = item.get("title", "Unknown")

                if is_low_quality_game(title):
                    continue

                rating = int(
                    float(
                        item.get(
                            "steamRatingPercent",
                            0
                        )
                    )
                )

                discount = int(
                    float(
                        item.get("savings", 0)
                    )
                )

                reviews = int(
                    item.get(
                        "steamRatingCount",
                        0
                    )
                )

                app_id = item.get("steamAppID")

                image = (
                    f"https://shared.fastly.steamstatic.com/"
                    f"store_item_assets/steam/apps/"
                    f"{app_id}/header.jpg"
                )

                game = GameDeal(
                    title=title,
                    original_price=f'{item.get("normalPrice")}$',
                    discounted_price=f'{item.get("salePrice")}$',
                    discount_percent=discount,
                    rating_percent=rating,
                    rating_text="Очень положительные",
                    description=generate_short_description(
                        title
                    ),
                    url=f"https://store.steampowered.com/app/{app_id}",
                    store="Steam",
                    image=image
                )

                games.append(game)

            except:
                continue

        games.sort(
            key=lambda x: (
                x.rating_percent,
                x.discount_percent
            ),
            reverse=True
        )

        set_cache("steam_deals", games)

        return games

    except:
        return []


async def get_steam_free_games():

    cached = get_cache("steam_free")

    if cached:
        return cached

    games = []

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                "https://store.steampowered.com/api/featuredcategories",
                timeout=20
            ) as response:

                data = await response.json()

        featured = data.get("specials", {}).get("items", [])

        for item in featured:

            try:

                final_price = item.get("final_price", 1)

                if final_price != 0:
                    continue

                title = item.get("name")

                if is_low_quality_game(title):
                    continue

                app_id = item.get("id")

                image = item.get("header_image")

                game = GameDeal(
                    title=title,
                    original_price="—",
                    discounted_price="БЕСПЛАТНО",
                    discount_percent=100,
                    rating_percent=90,
                    rating_text="Хорошие отзывы",
                    description=generate_short_description(
                        title
                    ),
                    url=f"https://store.steampowered.com/app/{app_id}",
                    store="Steam",
                    image=image,
                    is_free=True
                )

                games.append(game)

            except:
                continue

        set_cache("steam_free", games)

        return games

    except:
        return []