"""
Сервис поиска игр с поддержкой:
- fuzzy search (нечёткий поиск)
- нормализация названий (русский/английский)
- транслитерация
- поиск по неполному названию
- поиск напрямую через Steam/Epic API (если кэш пуст)
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
    'rdr': 'red dead redemption',
    'rdr2': 'red dead redemption 2',
    'witcher': 'ведьмак',
    'cyberpunk': 'cyberpunk 2077',
    'kcd': 'kingdom come deliverance',
    'hzd': 'horizon zero dawn',
    'tlou': 'the last of us',
    'metro exodus': 'metro exodus',
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

    # Проверяем синонимы
    if query in SYNONYMS:
        expansions.append(SYNONYMS[query])

    # Проверяем, не является ли запрос синонимом для чего-то
    for key, value in SYNONYMS.items():
        if query == value:
            expansions.append(key)
            break

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
    Сначала ищет в кэше БД, если пусто — через Steam API.
    """
    # 1. Сначала ищем в кэше БД
    games = await get_all_deals_for_search()
    if games:
        results = _fuzzy_search_in_list(query, games, threshold)
        if results:
            return results

    # 2. Если кэш пуст или ничего не нашли — ищем через API
    try:
        api_results = await _search_steam_api(query)
        if api_results:
            return api_results
    except Exception:
        pass

    # 3. Пробуем ещё поиск через CheapShark (Steam deals)
    try:
        cs_results = await _search_cheapshark(query)
        if cs_results:
            return cs_results
    except Exception:
        pass

    return []


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
                    score = max(score, partial_score)

                if score >= threshold:
                    results[key] = {**game, "match_score": score}
                    seen_titles.add(key)
                    break

    sorted_results = sorted(
        results.values(),
        key=lambda x: (-x["match_score"], x["title"])
    )
    return sorted_results[:20]


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