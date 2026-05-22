"""
Сервис поиска игр с поддержкой:
- fuzzy search (нечёткий поиск)
- нормализация названий (русский/английский)
- транслитерация
- поиск по неполному названию
- поиск напрямую через Steam/Epic API (если кэш пуст)
- поиск с учётом похожих названий
"""

import re
import aiohttp
from rapidfuzz import fuzz

from database import get_all_deals_for_search, get_deals_from_cache, get_free_from_cache


# ─── Нормализация ────────────────────────────────

# Словарь транслитерации кириллица -> латиница
TRANSLIT_TABLE = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
}

# Известные синонимы/сокращения
SYNONYMS = {
    'gta': 'grand theft auto',
    'gtav': 'grand theft auto v',
    'gta5': 'grand theft auto v',
    'gta 5': 'grand theft auto v',
    'rdr': 'red dead redemption',
    'rdr2': 'red dead redemption 2',
    'rdr 2': 'red dead redemption 2',
    'witcher': 'ведьмак',
    'cyberpunk': 'cyberpunk 2077',
    'cp2077': 'cyberpunk 2077',
    'kcd': 'kingdom come deliverance',
    'hzd': 'horizon zero dawn',
    'tlou': 'the last of us',
    'metro': 'metro exodus',
    'battlefield': 'battlefield',
    'bf': 'battlefield',
    'bf1': 'battlefield 1',
    'bf5': 'battlefield v',
    'bf2042': 'battlefield 2042',
    'ac': 'assassin\'s creed',
    'dark souls': 'dark souls',
    'ds': 'dark souls',
    'ds3': 'dark souls iii',
    'ds2': 'dark souls ii',
    'er': 'elden ring',
    'lol': 'league of legends',
    'cs': 'counter strike',
    'csgo': 'counter strike 2',
    'cs2': 'counter strike 2',
    'dota': 'dota 2',
    'dota2': 'dota 2',
    'pubg': 'playerunknown\'s battlegrounds',
    'minecraft': 'minecraft',
    'mc': 'minecraft',
    'fifa': 'fifa',
    'nba': 'nba 2k',
    'cod': 'call of duty',
    'mw': 'modern warfare',
    'bdo': 'black desert online',
    'skyrim': 'the elder scrolls v skyrim',
    'tes': 'the elder scrolls',
    'hl': 'half life',
    'hl2': 'half life 2',
    'portal': 'portal',
    'l4d': 'left 4 dead',
    'l4d2': 'left 4 dead 2',
}

# Популярные числовые замены
NUMBER_MAP = {
    '5': 'v', '4': 'iv', '3': 'iii', '2': 'ii', '1': 'i',
    'v': '5', 'iv': '4', 'iii': '3', 'ii': '2', 'i': '1',
}


def transliterate(text: str) -> str:
    """Транслитерация русского текста в латиницу."""
    result = []
    for char in text:
        result.append(TRANSLIT_TABLE.get(char, char))
    return ''.join(result)


def normalize_title(title: str) -> tuple:
    """
    Нормализация названия игры:
    - нижний регистр
    - удаление лишних пробелов
    - удаление спецсимволов
    - транслитерация
    """
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    translit = transliterate(title)
    return title, translit


def expand_query(query: str) -> list[str]:
    """Расширяет поисковый запрос синонимами и вариациями."""
    query = query.lower().strip()
    expansions = [query]

    # Добавляем транслитерацию
    _, translit = normalize_title(query)
    if translit != query:
        expansions.append(translit)

    # Сначала проверим, содержит ли запрос ключевое слово из синонимов
    query_lower = query.lower()
    for key, value in SYNONYMS.items():
        if query_lower == key:
            expansions.append(value)
        elif query_lower == value:
            expansions.append(key)
        # Частичное совпадение: если ключ содержится в запросе
        elif len(key) > 2 and key in query_lower:
            expansions.append(value)

    # Заменяем римские/арабские цифры
    words = query.split()
    for i, word in enumerate(words):
        if word in NUMBER_MAP:
            alt_words = words.copy()
            alt_words[i] = NUMBER_MAP[word]
            expansions.append(' '.join(alt_words))

    return list(set(expansions))


async def search_games(query: str, threshold: int = 60) -> list[dict]:
    """
    Поиск игр по названию с fuzzy search.
    Сначала ищет в кэше БД, если пусто — через Steam API и Epic API.
    """
    # 1. Сначала ищем в кэше БД
    games = await get_all_deals_for_search()
    if games:
        results = _fuzzy_search_in_list(query, games, threshold)
        if results:
            return results

    # 2. Если кэш пуст или ничего не нашли — ищем через API
    api_results = []
    
    # Steam API
    try:
        steam_results = await _search_steam_api(query)
        api_results.extend(steam_results)
    except Exception:
        pass

    # CheapShark (ещё один Steam API)
    if not api_results:
        try:
            cs_results = await _search_cheapshark(query)
            api_results.extend(cs_results)
        except Exception:
            pass

    # Epic Games API
    try:
        epic_results = await _search_epic_api(query)
        api_results.extend(epic_results)
    except Exception:
        pass

    # Удаляем дубликаты по названию
    seen = set()
    unique_results = []
    for r in api_results:
        key = f"{r['title'].lower()}|{r['store']}"
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results[:20]


def _fuzzy_search_in_list(query: str, games: list[dict], threshold: int = 60) -> list[dict]:
    """Fuzzy search по списку игр."""
    expansions = expand_query(query)
    results = {}
    seen_titles = set()

    for expansion in expansions:
        for game in games:
            game_norm, game_translit = normalize_title(game["title"])
            key = f"{game['title']}|{game['store']}"

            if key in seen_titles:
                continue

            candidates = [
                game_norm,
                game_translit,
                game["title"].lower(),
            ]

            for candidate in candidates:
                if expansion == candidate or expansion in candidate:
                    score = 100
                else:
                    score = fuzz.ratio(expansion, candidate)
                    partial_score = fuzz.partial_ratio(expansion, candidate)
                    token_score = fuzz.token_sort_ratio(expansion, candidate)
                    score = max(score, partial_score, token_score)

                if score >= threshold:
                    results[key] = {**game, "match_score": score}
                    seen_titles.add(key)
                    break

    sorted_results = sorted(
        results.values(),
        key=lambda x: (-x["match_score"], x["title"])
    )
    return sorted_results[:30]


async def _search_steam_api(query: str) -> list[dict]:
    """Поиск через Steam Store API."""
    url = "https://store.steampowered.com/api/storesearch"
    params = {
        "term": query,
        "l": "english",
        "cc": "RU",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=15) as resp:
            data = await resp.json()

    items = data.get("items", [])
    results = []

    for item in items[:15]:
        name = item.get("name", "Unknown")
        app_id = item.get("id")

        if not app_id:
            continue

        image = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"
        url = f"https://store.steampowered.com/app/{app_id}"

        results.append({
            "title": name,
            "store": "Steam",
            "price": 0,
            "original_price": 0,
            "discount_percent": 0,
            "is_free": False,
            "url": url,
            "image": image,
            "match_score": 85,
        })

    return results


async def _search_cheapshark(query: str) -> list[dict]:
    """Поиск через CheapShark API (скидки Steam)."""
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {
        "title": query,
        "storeID": 1,
        "pageSize": 20,
        "exact": 0,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=15) as resp:
            data = await resp.json()

    if not data:
        return []

    results = []
    for item in data:
        title = item.get("title", "Unknown")
        app_id = item.get("steamAppID")

        if not app_id:
            continue

        discount = int(float(item.get("savings", 0)))
        sale_price = float(item.get("salePrice", 0))
        normal_price = float(item.get("normalPrice", 0))
        image = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"

        results.append({
            "title": title,
            "store": "Steam",
            "price": sale_price,
            "original_price": normal_price,
            "discount_percent": discount,
            "is_free": sale_price == 0,
            "url": f"https://store.steampowered.com/app/{app_id}",
            "image": image,
            "match_score": 80,
        })

    return results[:15]


async def _search_epic_api(query: str) -> list[dict]:
    """Поиск через Epic Games Store API."""
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as resp:
            data = await resp.json()

    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    results = []

    query_lower = query.lower().strip()

    for item in elements:
        try:
            title = item.get("title", "")
            if not title:
                continue

            # Проверяем на совпадение с запросом
            title_lower = title.lower()
            if query_lower not in title_lower:
                # Fuzzy match для Epic
                title_norm, title_translit = normalize_title(title)
                query_norm, query_translit = normalize_title(query)
                ratio = max(
                    fuzz.partial_ratio(query_lower, title_lower),
                    fuzz.partial_ratio(query_norm, title_norm),
                    fuzz.partial_ratio(query_translit, title_translit),
                )
                if ratio < 60:
                    continue

            slug = item.get("productSlug")
            if not slug:
                # Пробуем получить slug из url
                url_mappings = item.get("urlMappings", [])
                if url_mappings:
                    slug = url_mappings[0].get("pageSlug", "")
                if not slug:
                    continue

            # Получаем цену
            price_info = item.get("price", {}).get("totalPrice", {})
            discount_price = price_info.get("discountPrice", 0)
            original_price = price_info.get("originalPrice", 0)
            is_free = discount_price == 0

            # Получаем изображение
            image = None
            for img in item.get("keyImages", []):
                if img.get("type") in ("OfferImageWide", "DieselStoreFrontWide"):
                    image = img.get("url")
                    break

            results.append({
                "title": title,
                "store": "Epic Games",
                "price": discount_price / 100 if discount_price else 0,
                "original_price": original_price / 100 if original_price else 0,
                "discount_percent": 100 if is_free else 0,
                "is_free": is_free,
                "url": f"https://store.epicgames.com/p/{slug}",
                "image": image or "",
                "match_score": 80,
            })
        except Exception:
            continue

    return results[:15]


async def search_by_exact_prefix(query: str) -> list[dict]:
    """Поиск по началу названия (для подсказок при вводе)."""
    query = query.lower().strip()
    games = await get_all_deals_for_search()

    results = []
    seen = set()

    for game in games:
        key = f"{game['title']}|{game['store']}"
        if key in seen:
            continue

        title_lower = game["title"].lower()
        _, translit = normalize_title(game["title"])

        if title_lower.startswith(query) or translit.startswith(query):
            results.append(game)
            seen.add(key)

    return results[:20]