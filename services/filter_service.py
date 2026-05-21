"""
Сервис фильтрации игр.

Применяет пользовательские фильтры к списку GameDeal и возвращает
отфильтрованный и отсортированный результат.
"""
from typing import List, Optional
from models import GameDeal

# ─── Словарь жанров для популярных игр ──────────────────────────
# Ключ: подстрока в названии игры (нижний регистр)
# Значение: список жанров
GENRE_MAP = {
    # RPG
    "final fantasy": ["RPG"],
    "elder scrolls": ["RPG", "Open World"],
    "skyrim": ["RPG", "Open World"],
    "witcher": ["RPG", "Action"],
    "baldur": ["RPG"],
    "divinity": ["RPG"],
    "dark souls": ["RPG", "Action"],
    "elden ring": ["RPG", "Action", "Open World"],
    "dragon age": ["RPG"],
    "mass effect": ["RPG", "Action"],
    "kingdom come": ["RPG"],
    "cyberpunk": ["RPG", "Open World"],
    "fallout": ["RPG", "Open World"],
    "path of exile": ["RPG", "Action"],
    "diablo": ["RPG", "Action"],
    "pillars of eternity": ["RPG"],
    "torment": ["RPG"],
    "nier": ["RPG", "Action"],
    "monster hunter": ["RPG", "Action"],
    "octopath": ["RPG"],
    "tales of": ["RPG"],
    "starfield": ["RPG", "Open World"],
    "banner saga": ["RPG", "Strategy"],
    "disco elysium": ["RPG"],
    "outward": ["RPG", "Survival"],
    "greedfall": ["RPG"],
    "vampyr": ["RPG", "Action"],
    "yakuza": ["RPG", "Action"],
    "persona": ["RPG"],
    "dragon quest": ["RPG"],
    "bravely": ["RPG"],
    "nier": ["RPG", "Action"],
    "xenoblade": ["RPG"],
    "fable": ["RPG"],
    "gothic": ["RPG"],
    "rise of the tomb raider": ["Action", "Adventure"],
    "shadow of the tomb raider": ["Action", "Adventure"],
    "crusader kings": ["Strategy", "Simulator"],
    "europa universalis": ["Strategy", "Simulator"],
    "hearts of iron": ["Strategy", "Simulator"],
    "stellaris": ["Strategy", "Simulator"],
    "civilization": ["Strategy"],
    "total war": ["Strategy"],
    "age of empires": ["Strategy"],
    "age of wonders": ["Strategy"],
    "xcom": ["Strategy"],
    "x-com": ["Strategy"],
    "frostpunk": ["Strategy", "Survival"],
    "banished": ["Strategy", "Survival"],
    "rimworld": ["Strategy", "Survival"],
    "factorio": ["Strategy", "Sandbox"],
    "satisfactory": ["Strategy", "Sandbox"],
    "dyson sphere": ["Strategy", "Sandbox"],
    "prison architect": ["Strategy", "Simulator"],
    "cities: skylines": ["Simulator", "Strategy"],
    "city skylines": ["Simulator", "Strategy"],
    "planet coaster": ["Simulator"],
    "planet zoo": ["Simulator"],
    "rollercoaster tycoon": ["Simulator"],
    "the sims": ["Simulator", "Casual"],
    "flight simulator": ["Simulator"],
    "euro truck": ["Simulator"],
    "farming simulator": ["Simulator"],
    "kerbal": ["Simulator"],
    "hollow knight": ["Action", "Adventure"],
    "hades": ["Action", "RPG"],
    "dead cells": ["Action"],
    "celeste": ["Action", "Adventure"],
    "cuphead": ["Action"],
    "doom": ["Action", "Shooter"],
    "doom eternal": ["Shooter", "Action"],
    "quake": ["Shooter"],
    "call of duty": ["Shooter", "Action"],
    "battlefield": ["Shooter", "Action"],
    "counter-strike": ["Shooter"],
    "csgo": ["Shooter"],
    "cs:go": ["Shooter"],
    "overwatch": ["Shooter"],
    "team fortress": ["Shooter"],
    "titanfall": ["Shooter"],
    "destiny": ["Shooter", "Action"],
    "borderlands": ["Shooter", "RPG"],
    "far cry": ["Shooter", "Open World"],
    "crysis": ["Shooter"],
    "metro": ["Shooter", "Horror"],
    "half-life": ["Shooter"],
    "left 4 dead": ["Shooter"],
    "payday": ["Shooter"],
    "rainbow six": ["Shooter"],
    "ghost recon": ["Shooter", "Action"],
    "resident evil": ["Horror", "Action"],
    "silent hill": ["Horror"],
    "amnesia": ["Horror"],
    "outlast": ["Horror"],
    "alien isolation": ["Horror"],
    "dead space": ["Horror", "Shooter"],
    "evil within": ["Horror"],
    "layers of fear": ["Horror"],
    "subnautica": ["Survival", "Adventure"],
    "the forest": ["Survival", "Horror"],
    "green hell": ["Survival"],
    "stranded deep": ["Survival"],
    "raft": ["Survival"],
    "dont starve": ["Survival"],
    "valheim": ["Survival", "Action"],
    "ark": ["Survival", "Action"],
    "conan exiles": ["Survival", "Action"],
    "minecraft": ["Sandbox", "Survival"],
    "terraria": ["Sandbox", "Adventure"],
    "stardew valley": ["Simulator", "Casual"],
    "no man's sky": ["Sandbox", "Survival"],
    "garry's mod": ["Sandbox"],
    "scrap mechanic": ["Sandbox"],
    "besiege": ["Sandbox"],
    "world of warcraft": ["MMO", "RPG"],
    "wow": ["MMO", "RPG"],
    "final fantasy xiv": ["MMO", "RPG"],
    "ffxiv": ["MMO", "RPG"],
    "guild wars": ["MMO", "RPG"],
    "elder scrolls online": ["MMO", "RPG"],
    "eso": ["MMO", "RPG"],
    "black desert": ["MMO", "RPG"],
    "albion": ["MMO"],
    "runescape": ["MMO", "RPG"],
    "warframe": ["MMO", "Shooter"],
    "destiny 2": ["MMO", "Shooter"],
    "fifa": ["Sport"],
    "football manager": ["Sport", "Simulator"],
    "pro evolution soccer": ["Sport"],
    "nba": ["Sport"],
    "madden": ["Sport"],
    "racing": ["Racing"],
    "need for speed": ["Racing"],
    "forza": ["Racing"],
    "gran turismo": ["Racing"],
    "assetto": ["Racing"],
    "dirt": ["Racing"],
    "f1": ["Racing"],
    "nascar": ["Racing"],
    "grid": ["Racing"],
    "project cars": ["Racing"],
    "anime": ["Anime"],
    "senran": ["Anime"],
    "visual novel": ["Anime"],
    "galaxy angel": ["Anime"],
    "hyperdimension": ["Anime"],
    "steins gate": ["Anime"],
    "doki doki": ["Anime"],
    "hatoful": ["Anime"],
    "cat quest": ["Casual", "RPG"],
    "hidden": ["Casual", "Adventure"],
    "puzzle": ["Casual"],
    "match 3": ["Casual"],
    "candy": ["Casual"],
    "word": ["Casual"],
    "solitaire": ["Casual"],
    "grand theft auto": ["Action", "Open World"],
    "gta": ["Action", "Open World"],
    "red dead": ["Action", "Open World"],
    "read dead": ["Action", "Open World"],
    "assassin's creed": ["Action", "Open World"],
    "assassins creed": ["Action", "Open World"],
    "watch dogs": ["Action", "Open World"],
    "ghost of tsushima": ["Action", "Open World"],
    "horizon": ["Action", "Open World", "RPG"],
    "days gone": ["Action", "Open World"],
    "spider-man": ["Action", "Open World"],
    "spiderman": ["Action", "Open World"],
    "batman": ["Action", "Adventure"],
    "middle-earth": ["Action", "RPG"],
    "just cause": ["Action", "Open World"],
    "saints row": ["Action", "Open World"],
    "mafia": ["Action", "Open World"],
    "dying light": ["Action", "Survival", "Horror"],
    "dead island": ["Action", "Survival"],
    "left 4 dead": ["Action", "Shooter"],
    "god of war": ["Action", "Adventure"],
    "devil may cry": ["Action"],
    "bayonetta": ["Action"],
    "metal gear": ["Action", "Stealth"],
    "hitman": ["Action", "Stealth"],
    "splinter cell": ["Action", "Stealth"],
    "dishonored": ["Action", "Stealth"],
    "prey": ["Action", "Horror"],
    "bioshock": ["Shooter", "Horror"],
    "wolfenstein": ["Shooter"],
    "serious sam": ["Shooter"],
    "painkiller": ["Shooter"],
    "bulletstorm": ["Shooter"],
    "ror2": ["Action", "Roguelike"],
    "risk of rain": ["Action", "Roguelike"],
    "binding of isaac": ["Action", "Roguelike"],
    "enter the gungeon": ["Action", "Roguelike"],
    "slay the spire": ["Strategy", "Card"],
    "darkest dungeon": ["RPG", "Horror"],
    "ftl": ["Strategy", "Roguelike"],
    "into the breach": ["Strategy"],
    "returnal": ["Action", "Roguelike"],
    "hades": ["Action", "Roguelike"],
    "dead cells": ["Action", "Roguelike"],
    "vampire survivors": ["Action", "Casual"],
    "broforce": ["Action", "Casual"],
    "human fall flat": ["Casual", "Adventure"],
    "gang beasts": ["Casual", "Action"],
    "among us": ["Casual", "Multiplayer"],
    "fall guys": ["Casual", "Multiplayer"],
    "party": ["Casual"],
    "mini": ["Casual"],
    "goat simulator": ["Casual", "Sandbox"],
    "untitled goose": ["Casual", "Adventure"],
    "portal": ["Action", "Puzzle"],
    "the witness": ["Puzzle", "Adventure"],
    "talos": ["Puzzle"],
    "obduction": ["Puzzle", "Adventure"],
    "myst": ["Puzzle", "Adventure"],
    "limbo": ["Adventure", "Horror"],
    "inside": ["Adventure", "Horror"],
    "little nightmares": ["Adventure", "Horror"],
    "firewatch": ["Adventure"],
    "walking dead": ["Adventure"],
    "life is strange": ["Adventure"],
    "telltale": ["Adventure"],
    "heavy rain": ["Adventure"],
    "detroit": ["Adventure"],
    "beyond two souls": ["Adventure"],
    "what remains": ["Adventure"],
    "journey": ["Adventure", "Casual"],
    "abzu": ["Adventure", "Casual"],
    "flower": ["Adventure", "Casual"],
    "dark souls": ["RPG", "Action"],
    "sekiro": ["Action", "RPG"],
    "bloodborne": ["RPG", "Action"],
    "nioh": ["RPG", "Action"],
    "code vein": ["RPG", "Action"],
    "remnant": ["Shooter", "RPG"],
    "control": ["Action", "Adventure"],
    "alan wake": ["Horror", "Action"],
    "quantum break": ["Action"],
    "plague tale": ["Adventure", "Horror"],
    "hellblade": ["Action", "Adventure"],
    "kena": ["Action", "Adventure"],
    "immortals fenyx": ["Action", "Open World", "RPG"],
}

# ─── Дефолтные жанры по ключевым словам ──────────────────────
KEYWORD_GENRES = {
    "zombie": ["Horror", "Action"],
    "survival": ["Survival"],
    "shooter": ["Shooter"],
    "fps": ["Shooter"],
    "tps": ["Shooter"],
    "strategy": ["Strategy"],
    "simulator": ["Simulator"],
    "rpg": ["RPG"],
    "action": ["Action"],
    "adventure": ["Adventure"],
    "horror": ["Horror"],
    "racing": ["Racing"],
    "sport": ["Sport"],
    "puzzle": ["Casual", "Puzzle"],
    "mmo": ["MMO"],
    "battle royale": ["Shooter", "Action"],
    "roguelike": ["Action", "Roguelike"],
    "rogue-lite": ["Action", "Roguelike"],
    "roguelite": ["Action", "Roguelike"],
    "sandbox": ["Sandbox"],
    "open world": ["Open World"],
    "co-op": ["Multiplayer"],
    "coop": ["Multiplayer"],
    "multiplayer": ["Multiplayer"],
    "online": ["Multiplayer"],
    "pvp": ["Multiplayer", "Action"],
    "anime": ["Anime"],
    "indie": ["Indie"],
    "open world": ["Open World"],
}

# ─── Доступные жанры для фильтрации ─────────────────────────
ALL_GENRES = [
    "Action", "Shooter", "RPG", "Indie", "Simulator",
    "Strategy", "Survival", "Horror", "Racing", "Adventure",
    "MMO", "Anime", "Casual", "Sport", "Sandbox",
    "Open World", "Puzzle", "Roguelike", "Multiplayer",
]


def get_game_genres(title: str) -> List[str]:
    """Определить жанры игры по её названию."""
    title_lower = title.lower()

    # 1. Проверяем точное совпадение по словарю
    for key, genres in GENRE_MAP.items():
        if key in title_lower:
            return genres

    # 2. Проверяем по ключевым словам
    found = []
    for keyword, genres in KEYWORD_GENRES.items():
        if keyword in title_lower:
            for g in genres:
                if g not in found:
                    found.append(g)

    if found:
        return found

    # 3. По умолчанию — Action/Indie (для всего остального)
    return ["Action", "Indie"]


def filter_by_genres(games: List[GameDeal], selected_genres: List[str]) -> List[GameDeal]:
    """Оставить только игры, жанры которых пересекаются с выбранными."""
    if not selected_genres:
        return games
    selected_lower = [g.lower() for g in selected_genres]
    result = []
    for game in games:
        game_genres_lower = [gg.lower() for gg in game.genres]
        if any(sg in game_genres_lower for sg in selected_lower):
            result.append(game)
    return result


def filter_by_discount(games: List[GameDeal], min_discount: int) -> List[GameDeal]:
    """Оставить игры со скидкой >= min_discount."""
    if min_discount <= 0:
        return games
    return [g for g in games if g.discount_percent >= min_discount]


def filter_by_price(games: List[GameDeal], max_price: float) -> List[GameDeal]:
    """Оставить игры с ценой <= max_price (учитывает текущую цену)."""
    if max_price <= 0:
        return games
    result = []
    for game in games:
        # Парсим discounted_price в число
        price_str = game.discounted_price.lower().replace("$", "").replace("₽", "").replace(",", ".").strip()
        try:
            price_val = float(price_str)
            if price_val <= max_price:
                result.append(game)
        except (ValueError, TypeError):
            # Бесплатные игры попадают если max_price >= 0
            if game.is_free:
                result.append(game)
    return result


def filter_by_platform(games: List[GameDeal], platform: str) -> List[GameDeal]:
    """Оставить игры по платформе (steam / epic / all)."""
    if platform == "all":
        return games
    platform_lower = platform.lower()
    return [g for g in games if g.store.lower() == platform_lower]


def filter_by_type(games: List[GameDeal], filter_type: str) -> List[GameDeal]:
    """Фильтр по типу: discounts / free / all."""
    if filter_type == "all":
        return games
    if filter_type == "free":
        return [g for g in games if g.is_free]
    if filter_type == "discounts":
        return [g for g in games if not g.is_free and g.discount_percent > 0]
    return games


def filter_by_rating(games: List[GameDeal], min_rating: int) -> List[GameDeal]:
    """Оставить игры с рейтингом >= min_rating."""
    if min_rating <= 0:
        return games
    return [g for g in games if g.rating_percent >= min_rating]


def sort_games(games: List[GameDeal], sort_type: str) -> List[GameDeal]:
    """Отсортировать игры по заданному типу."""
    if sort_type == "discount":
        return sorted(games, key=lambda g: g.discount_percent, reverse=True)
    elif sort_type == "price":
        def price_key(g):
            try:
                return float(g.discounted_price.lower().replace("$", "").replace("₽", "").replace(",", ".").strip())
            except:
                return 0 if g.is_free else 999999
        return sorted(games, key=price_key)
    elif sort_type == "rating":
        return sorted(games, key=lambda g: g.rating_percent, reverse=True)
    elif sort_type == "title":
        return sorted(games, key=lambda g: g.title.lower())
    elif sort_type == "popularity":
        return sorted(games, key=lambda g: g.rating_percent, reverse=True)
    elif sort_type == "newest":
        # Возвращаем как есть (порядок из API считается "новизна")
        return games
    return games


def apply_filters(
    games: List[GameDeal],
    selected_genres: Optional[List[str]] = None,
    min_discount: int = 0,
    max_price: float = 0,
    platform: str = "all",
    filter_type: str = "all",
    sort_type: str = "discount",
    rating_filter: int = 0,
) -> List[GameDeal]:
    """
    Последовательно применить все фильтры к списку игр.

    1. По типу (скидки / халява)
    2. По платформе
    3. По жанрам
    4. По минимальной скидке
    5. По максимальной цене
    6. По рейтингу
    7. Сортировка
    """
    if not games:
        return []

    # Убедимся, что у каждой игры определены жанры
    for game in games:
        if not game.genres:
            game.genres = get_game_genres(game.title)

    # Применяем фильтры последовательно
    result = games
    result = filter_by_type(result, filter_type)
    result = filter_by_platform(result, platform)
    if selected_genres:
        result = filter_by_genres(result, selected_genres)
    result = filter_by_discount(result, min_discount)
    result = filter_by_price(result, max_price)
    result = filter_by_rating(result, rating_filter)
    result = sort_games(result, sort_type)

    return result


def format_active_filters(filters: dict) -> str:
    """Сформировать текст с описанием активных фильтров."""
    lines = ["🎮 <b>Текущие фильтры:</b>\n"]

    genres = filters.get("selected_genres", [])
    if genres:
        lines.append(f"🎭 Жанры: <b>{', '.join(genres)}</b>")
    else:
        lines.append("🎭 Жанры: <b>Все</b>")

    md = filters.get("min_discount", 0)
    if md > 0:
        lines.append(f"💸 Мин. скидка: <b>{md}%</b>")
    else:
        lines.append(f"💸 Мин. скидка: <b>Любая</b>")

    mp = filters.get("max_price", 0)
    if mp > 0:
        lines.append(f"💰 Макс. цена: <b>${mp}</b>")
    else:
        lines.append("💰 Макс. цена: <b>Любая</b>")

    plat = filters.get("platform", "all")
    plat_names = {"all": "Все", "steam": "Steam", "epic games": "Epic Games"}
    lines.append(f"🖥 Платформа: <b>{plat_names.get(plat, plat)}</b>")

    ft = filters.get("filter_type", "all")
    ft_names = {"all": "Все", "discounts": "Только скидки", "free": "Только халява"}
    lines.append(f"🎯 Тип: <b>{ft_names.get(ft, ft)}</b>")

    st = filters.get("sort_type", "discount")
    st_names = {"discount": "По скидке", "price": "По цене", "rating": "По рейтингу",
                 "title": "По алфавиту", "popularity": "По популярности", "newest": "По новизне"}
    lines.append(f"📊 Сортировка: <b>{st_names.get(st, st)}</b>")

    rf = filters.get("rating_filter", 0)
    if rf > 0:
        lines.append(f"⭐ Рейтинг: <b>{rf}%+</b>")

    return "\n".join(lines)