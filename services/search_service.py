"""
Сервис поиска игр с поддержкой:
- fuzzy search (нечёткий поиск)
- нормализация названий (русский/английский)
- транслитерация
- поиск по неполному названию
"""

import re
from rapidfuzz import fuzz, process

from database import get_all_deals_for_search


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
    'soma': 'soma',
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


def normalize_title(title: str) -> str:
    """
    Нормализация названия игры:
    - нижний регистр
    - удаление лишних пробелов
    - удаление спецсимволов
    - транслитерация кириллицы
    - замена цифр на римские/арабские
    """
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()

    # Пробуем транслитерировать
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
    Возвращает список найденных игр, отсортированный по релевантности.
    """
    games = await get_all_deals_for_search()
    if not games:
        return []

    # Нормализуем запрос
    norm_query, translit_query = normalize_title(query)
    expansions = expand_query(query)

    results = {}
    seen_titles = set()

    for expansion in expansions:
        # Точное совпадение
        for game in games:
            game_norm, game_translit = normalize_title(game["title"])
            key = f"{game['title']}|{game['store']}"

            if key in seen_titles:
                continue

            # Проверяем все варианты
            candidates = [
                game_norm,
                game_translit,
                game["title"].lower(),
            ]

            for candidate in candidates:
                # Точное совпадение
                if expansion == candidate or expansion in candidate:
                    score = 100
                else:
                    # Fuzzy match
                    score = fuzz.ratio(expansion, candidate)
                    # Частичное совпадение (подстрока)
                    partial_score = fuzz.partial_ratio(expansion, candidate)
                    score = max(score, partial_score)

                if score >= threshold:
                    results[key] = {
                        **game,
                        "match_score": score,
                    }
                    seen_titles.add(key)
                    break

    # Сортируем по релевантности
    sorted_results = sorted(
        results.values(),
        key=lambda x: (-x["match_score"], x["title"])
    )

    return sorted_results[:20]


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