"""
Сервис поиска игр с поддержкой:
- Поиск через Steam Store API, Epic Games GraphQL API
- Поиск через CheapShark (скидки Steam)
- Fuzzy search по локальному кэшу БД
- База KNOWN_GAMES для гарантированного поиска популярных игр
- Расширение запросов (синонимы, транслитерация)
"""

import re
import aiohttp
from rapidfuzz import fuzz

from database import get_all_deals_for_search


# ─── Транслитерация ──────────────────────────────

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

# ─── Синонимы (сокращение → полное название) ─────
SYNONYMS = {
    'gta': 'grand theft auto',
    'gtav': 'grand theft auto v', 'gta5': 'grand theft auto v',
    'gta 5': 'grand theft auto v', 'gta v': 'grand theft auto v',
    'gtasa': 'grand theft auto san andreas', 'gtavc': 'grand theft auto vice city',
    'gta4': 'grand theft auto iv', 'gta iv': 'grand theft auto iv',
    'rdr': 'red dead redemption', 'rdr2': 'red dead redemption 2',
    'rdr 2': 'red dead redemption 2', 'rdr1': 'red dead redemption',
    'witcher': 'the witcher', 'w3': 'the witcher 3 wild hunt', 'tw3': 'the witcher 3 wild hunt',
    'cyberpunk': 'cyberpunk 2077', 'cp2077': 'cyberpunk 2077',
    'kcd': 'kingdom come deliverance', 'hzd': 'horizon zero dawn', 'tlou': 'the last of us',
    'bg3': "baldur's gate 3", 'baldurs gate 3': "baldur's gate 3", 'baldurs gate': "baldur's gate",
    'divinity': 'divinity original sin', 'dos2': 'divinity original sin 2',
    'sekiro': 'sekiro shadows die twice', 'elden ring': 'elden ring', 'er': 'elden ring',
    'starfield': 'starfield', 'hogwarts': 'hogwarts legacy',
    'spiderman': 'marvels spider man', 'spider man': 'marvels spider man',
    'battlefield': 'battlefield', 'bf1': 'battlefield 1', 'bf5': 'battlefield v', 'bf2042': 'battlefield 2042',
    'fc': 'far cry', 'fc3': 'far cry 3', 'fc4': 'far cry 4', 'fc5': 'far cry 5', 'fc6': 'far cry 6',
    'ac': "assassin's creed", 'assassins creed': "assassin's creed",
    'cod': 'call of duty', 'mw': 'call of duty modern warfare',
    'ds': 'dark souls', 'ds1': 'dark souls', 'ds2': 'dark souls ii', 'ds3': 'dark souls iii',
    'me': 'mass effect', 'da': 'dragon age',
    'fnv': 'fallout new vegas', 'f4': 'fallout 4', 'f3': 'fallout 3',
    'skyrim': 'the elder scrolls v skyrim', 'tes': 'the elder scrolls',
    'oblivion': 'the elder scrolls iv oblivion', 'morrowind': 'the elder scrolls iii morrowind',
    'hl': 'half life', 'hl2': 'half life 2', 'cs': 'counter strike',
    'csgo': 'counter strike 2', 'cs2': 'counter strike 2', 'l4d': 'left 4 dead', 'l4d2': 'left 4 dead 2',
    'stardew': 'stardew valley', 'hollow knight': 'hollow knight', 'terraria': 'terraria',
    'rimworld': 'rimworld', 'factorio': 'factorio', 'satisfactory': 'satisfactory',
    'subnautica': 'subnautica', 'valheim': 'valheim', 'dead cells': 'dead cells',
    'disco elysium': 'disco elysium', 'stalker': 's.t.a.l.k.e.r.',
    'minecraft': 'minecraft', 'mc': 'minecraft', 'fifa': 'fifa', 'nba': 'nba 2k',
    'pubg': "playerunknown's battlegrounds", 'bdo': 'black desert online',
    'lol': 'league of legends', 'dota': 'dota 2', 'dota2': 'dota 2',
    'portal': 'portal', 'just cause': 'just cause', 'jc': 'just cause',
    'jc3': 'just cause 3', 'jc4': 'just cause 4', 'tomb raider': 'tomb raider',
    'mgs': 'metal gear solid', 'metal gear': 'metal gear solid',
    're': 'resident evil', 're4': 'resident evil 4', 're2': 'resident evil 2',
    're3': 'resident evil 3', 're7': 'resident evil 7', 're8': 'resident evil village',
    'village': 'resident evil village', 'alan wake': 'alan wake', 'aw': 'alan wake',
    'aw2': 'alan wake 2', 'control': 'control', 'hellblade': 'hellblade',
    'ori': 'ori', 'cuphead': 'cuphead', 'celeste': 'celeste', 'undertale': 'undertale',
    'outer wilds': 'outer wilds', 'outer worlds': 'the outer worlds',
    'kingdom come': 'kingdom come deliverance',
    'age of empires': 'age of empires', 'aoe': 'age of empires',
    'aoe2': 'age of empires ii', 'aoe4': 'age of empires iv',
    'total war': 'total war', 'tw': 'total war', 'warhammer': 'warhammer',
    'bannerlord': 'mount and blade ii bannerlord', 'mount and blade': 'mount and blade', 'm&b': 'mount and blade',
    'star wars': 'star wars', 'sw': 'star wars',
    'xcom': "xcom", 'xcom2': "xcom 2", 'civ': 'civilization', 'civ6': 'civilization vi', 'civ5': 'civilization v',
    'pathfinder': 'pathfinder', 'bioshock': 'bioshock', 'doom': 'doom',
    'wolfenstein': 'wolfenstein', 'prey': 'prey', 'dishonored': 'dishonored',
    'hitman': 'hitman', 'crysis': 'crysis', 'dead space': 'dead space',
    'metro': 'metro exodus', 'plague tale': 'a plague tale', 'a plague tale': 'a plague tale',
    'god of war': 'god of war', 'star citizen': 'star citizen', 'sc': 'star citizen',
}

NUMBER_MAP = {
    '5': 'v', '4': 'iv', '3': 'iii', '2': 'ii', '1': 'i',
    'v': '5', 'iv': '4', 'iii': '3', 'ii': '2', 'i': '1',
}

STOP_WORDS = {'dlc', 'demo', 'soundtrack', 'bundle', 'pack', 'preorder',
              'pre order', 'wallpaper', 'toolkit', 'skin', 'screenshot',
              'expansion', 'season pass', 'avatar', 'artbook', 'art book',
              'costume', 'theme', 'ost', 'music', 'key', 'gift', 'card',
              'booster', 'emoticon', 'profile', 'background', 'mod', 'editor'}

# Гарантированный поиск для популярных игр, которые Steam API может не находить
# по сокращённым названиям.
KNOWN_GAMES = {
    "gta 5": {"title": "Grand Theft Auto V", "app_id": "271590", "store": "Steam"},
    "gta5": {"title": "Grand Theft Auto V", "app_id": "271590", "store": "Steam"},
    "gta v": {"title": "Grand Theft Auto V", "app_id": "271590", "store": "Steam"},
    "gta": {"title": "Grand Theft Auto V", "app_id": "271590", "store": "Steam"},
    "rdr2": {"title": "Red Dead Redemption 2", "app_id": "1174180", "store": "Steam"},
    "red dead redemption 2": {"title": "Red Dead Redemption 2", "app_id": "1174180", "store": "Steam"},
    "rdr": {"title": "Red Dead Redemption 2", "app_id": "1174180", "store": "Steam"},
    "cp2077": {"title": "Cyberpunk 2077", "app_id": "1091500", "store": "Steam"},
    "cyberpunk 2077": {"title": "Cyberpunk 2077", "app_id": "1091500", "store": "Steam"},
    "cyberpunk": {"title": "Cyberpunk 2077", "app_id": "1091500", "store": "Steam"},
    "witcher 3": {"title": "The Witcher 3: Wild Hunt", "app_id": "292030", "store": "Steam"},
    "the witcher 3": {"title": "The Witcher 3: Wild Hunt", "app_id": "292030", "store": "Steam"},
    "stardew valley": {"title": "Stardew Valley", "app_id": "413150", "store": "Steam"},
    "stardew": {"title": "Stardew Valley", "app_id": "413150", "store": "Steam"},
    "hollow knight": {"title": "Hollow Knight", "app_id": "367520", "store": "Steam"},
    "terraria": {"title": "Terraria", "app_id": "105600", "store": "Steam"},
    "elden ring": {"title": "ELDEN RING", "app_id": "1245620", "store": "Steam"},
    "er": {"title": "ELDEN RING", "app_id": "1245620", "store": "Steam"},
    "bg3": {"title": "Baldur's Gate 3", "app_id": "1086940", "store": "Steam"},
    "baldur's gate 3": {"title": "Baldur's Gate 3", "app_id": "1086940", "store": "Steam"},
    "dark souls 3": {"title": "DARK SOULS III", "app_id": "374320", "store": "Steam"},
    "dark souls": {"title": "DARK SOULS: REMASTERED", "app_id": "570940", "store": "Steam"},
    "skyrim": {"title": "The Elder Scrolls V: Skyrim Special Edition", "app_id": "489830", "store": "Steam"},
    "fallout 4": {"title": "Fallout 4", "app_id": "377160", "store": "Steam"},
    "new vegas": {"title": "Fallout: New Vegas", "app_id": "22380", "store": "Steam"},
    "fnv": {"title": "Fallout: New Vegas", "app_id": "22380", "store": "Steam"},
    "mass effect": {"title": "Mass Effect Legendary Edition", "app_id": "1328670", "store": "Steam"},
    "me": {"title": "Mass Effect Legendary Edition", "app_id": "1328670", "store": "Steam"},
    "portal 2": {"title": "Portal 2", "app_id": "620", "store": "Steam"},
    "portal": {"title": "Portal", "app_id": "400", "store": "Steam"},
    "half life 2": {"title": "Half-Life 2", "app_id": "220", "store": "Steam"},
    "hl2": {"title": "Half-Life 2", "app_id": "220", "store": "Steam"},
    "kcd": {"title": "Kingdom Come: Deliverance", "app_id": "379430", "store": "Steam"},
    "kingdom come": {"title": "Kingdom Come: Deliverance", "app_id": "379430", "store": "Steam"},
    "hades": {"title": "Hades", "app_id": "1145360", "store": "Steam"},
    "disco elysium": {"title": "Disco Elysium - The Final Cut", "app_id": "632470", "store": "Steam"},
    "resident evil 4": {"title": "Resident Evil 4", "app_id": "2050650", "store": "Steam"},
    "re4": {"title": "Resident Evil 4", "app_id": "2050650", "store": "Steam"},
    "starfield": {"title": "Starfield", "app_id": "1716740", "store": "Steam"},
    "hogwarts legacy": {"title": "Hogwarts Legacy", "app_id": "990080", "store": "Steam"},
    "hogwarts": {"title": "Hogwarts Legacy", "app_id": "990080", "store": "Steam"},
    "sekiro": {"title": "Sekiro: Shadows Die Twice", "app_id": "814380", "store": "Steam"},
    "doom": {"title": "DOOM Eternal", "app_id": "782330", "store": "Steam"},
    "bioshock": {"title": "BioShock Remastered", "app_id": "409710", "store": "Steam"},
}


def transliterate(text: str) -> str:
    result = []
    for char in text:
        result.append(TRANSLIT_TABLE.get(char, char))
    return ''.join(result)


def normalize_title(title: str) -> tuple:
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title, transliterate(title)


def is_low_quality(title: str) -> bool:
    title_lower = title.lower()
    for word in STOP_WORDS:
        if word in title_lower:
            return True
    return False


def expand_query(query: str) -> list[str]:
    original = query.lower().strip()
    expansions = {original}
    _, translit_result = normalize_title(original)
    if translit_result and translit_result != original:
        expansions.add(translit_result)
    for key, value in SYNONYMS.items():
        if original == key:
            expansions.add(value)
        elif original == value:
            expansions.add(key)
    words = original.split()
    for i, word in enumerate(words):
        if word in NUMBER_MAP:
            alt_words = words.copy()
            alt_words[i] = NUMBER_MAP[word]
            expansions.add(' '.join(alt_words))
    return list(expansions)


def make_known_game(query: str):
    """Создаёт результат из KNOWN_GAMES если запрос совпадает."""
    q = query.lower().strip()
    if q in KNOWN_GAMES:
        g = KNOWN_GAMES[q]
        return {
            "title": g["title"],
            "store": g["store"],
            "price": 0,
            "original_price": 0,
            "discount_percent": 0,
            "is_free": False,
            "url": f"https://store.steampowered.com/app/{g['app_id']}",
            "image": f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{g['app_id']}/header.jpg",
            "match_score": 100,
        }
    return None


def score_match(query: str, title: str) -> int:
    q = query.lower().strip()
    t = title.lower().strip()
    t_norm, t_trans = normalize_title(title)
    q_norm, q_trans = normalize_title(query)

    if t == q or t_norm == q_norm:
        return 100
    if q in t or q_norm in t_norm:
        return 95
    if t in q:
        return 90
    q_words = set(q.split())
    t_words = set(t.split())
    if q_words and q_words.issubset(t_words):
        return 92
    if q_trans and q_trans in t_norm:
        return 85
    if t_trans and q in t_trans:
        return 85
    return int(max(fuzz.WRatio(q_norm, t_norm), fuzz.token_sort_ratio(q_norm, t_norm), fuzz.partial_ratio(q_norm, t_norm)))


def score_match_expanded(query: str, title: str, expanded: list[str]) -> int:
    q = query.lower().strip()
    t = title.lower().strip()
    base = score_match(query, title)
    if base >= 90:
        return base
    for eq in expanded:
        if not eq or eq == q:
            continue
        eq_lower = eq.lower().strip()
        if eq_lower in t or t in eq_lower:
            if len(q) <= len(eq) * 0.6:
                return max(base, 97)
            return max(base, 92)
        eq_words = set(eq_lower.split())
        t_words = set(t.split())
        common = eq_words & t_words
        if len(common) >= 2 and len(common) >= len(eq_words) * 0.5:
            return max(base, 88)
    return base


def filter_and_sort(results: list[dict], query: str, min_score: int = 60) -> list[dict]:
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x.get("match_score", 0), reverse=True):
        key = f"{r['title'].lower().strip()}|{r['store']}"
        if key in seen:
            continue
        seen.add(key)
        score = int(r.get("match_score", 0))
        if score < min_score:
            continue
        if is_low_quality(r["title"]) and score < 85:
            continue
        r["match_score"] = score
        unique.append(r)
    return unique[:30]


async def search_games(query: str, threshold: int = 60) -> list[dict]:
    """
    Поиск игр. Стратегия:
    1. KNOWN_GAMES: гарантированный результат для популярных игр
    2. API: Steam + Epic со всеми вариантами запроса
    3. CheapShark: скидки
    4. Fuzzy по кэшу БД как fallback
    """
    expanded = expand_query(query)
    all_results = []
    seen_titles = {}
    variants = sorted(set(expanded), key=lambda x: (-len(x), x))

    # ─── ШАГ 1: KNOWN_GAMES (если есть) ────
    known = make_known_game(query)
    if known:
        key = f"{known['title'].lower().strip()}|{known['store']}"
        seen_titles[key] = 100
        known["match_score"] = 100
        all_results.append(known)
    # ─── ШАГ 2: API поиск ────
    for variant in variants:
        good_cnt = sum(1 for r in all_results if r.get("match_score", 0) >= 85)
        if good_cnt >= 5:
            break

        for task in [_search_steam_api(variant, 15), _search_epic_catalog_api(variant, 15)]:
            try:
                for r in await task:
                    key = f"{r['title'].lower().strip()}|{r['store']}"
                    score = score_match_expanded(query, r["title"], expanded)
                    if key not in seen_titles:
                        seen_titles[key] = score
                        r["match_score"] = score
                        all_results.append(r)
                    elif score > seen_titles[key]:
                        for existing in all_results:
                            if f"{existing['title'].lower().strip()}|{existing['store']}" == key:
                                existing["match_score"] = score
                                seen_titles[key] = score
                                break
            except Exception:
                pass

    # ─── ШАГ 3: CheapShark ────
    try:
        for r in await _search_cheapshark(query):
            key = f"{r['title'].lower().strip()}|{r['store']}"
            if key not in seen_titles:
                score = score_match_expanded(query, r["title"], expanded)
                seen_titles[key] = score
                r["match_score"] = score
                all_results.append(r)
    except Exception:
        pass

    if all_results:
        sorted_results = filter_and_sort(all_results, query, min_score=threshold)
        # Возвращаем если есть хотя бы 1 результат с высоким score, или минимум 3 любых
        if sorted_results:
            if len(sorted_results) >= 3 or sorted_results[0].get("match_score", 0) >= 90:
                return sorted_results

    # ─── ШАГ 4: Fuzzy по БД ────
    try:
        games = await get_all_deals_for_search()
        if games:
            results = _fuzzy_search(query, games)
            if results:
                return results
    except Exception:
        pass

    if all_results:
        return filter_and_sort(all_results, query, min_score=0)[:30]
    return []


def _fuzzy_search(query: str, games: list[dict], threshold: int = 55) -> list[dict]:
    expansions = expand_query(query)
    results = {}
    seen = set()
    for expansion in expansions:
        for game in games:
            title = game["title"]
            norm, transl = normalize_title(title)
            key = f"{title}|{game['store']}"
            if key in seen:
                continue
            for cand in [c for c in [title.lower(), norm, transl] if c]:
                if expansion == cand:
                    score = 100
                elif len(expansion) > 2 and expansion in cand:
                    score = 95
                elif len(cand) > 2 and cand in expansion:
                    score = 85
                else:
                    score = int(max(fuzz.ratio(expansion, cand), fuzz.partial_ratio(expansion, cand), fuzz.token_sort_ratio(expansion, cand), fuzz.WRatio(expansion, cand)))
                if score >= threshold:
                    results[key] = {**game, "match_score": score}
                    seen.add(key)
                    break
    return sorted(results.values(), key=lambda x: (-x["match_score"], x["title"]))[:30]


async def _search_steam_api(query: str, limit: int = 15) -> list[dict]:
    url = "https://store.steampowered.com/api/storesearch"
    results = []
    for lang in ["russian", "english"]:
        if results:
            break
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, params={"term": query, "l": lang, "cc": "RU"}, timeout=8) as r:
                    data = await r.json()
        except Exception:
            continue
        for item in data.get("items", [])[:limit]:
            name, app_id = item.get("name", ""), item.get("id")
            if not name or not app_id:
                continue
            results.append({
                "title": name, "store": "Steam",
                "price": 0, "original_price": 0, "discount_percent": 0, "is_free": False,
                "url": f"https://store.steampowered.com/app/{app_id}",
                "image": f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",
                "match_score": 0,
            })
    return results


async def _search_cheapshark(query: str) -> list[dict]:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://www.cheapshark.com/api/1.0/deals",
                             params={"title": query, "storeID": 1, "pageSize": 15, "exact": 0}, timeout=8) as r:
                data = await r.json()
    except Exception:
        return []
    if not data:
        return []
    results = []
    for item in data:
        title, app_id = item.get("title", ""), item.get("steamAppID")
        if not title or not app_id:
            continue
        results.append({
            "title": title, "store": "Steam",
            "price": float(item.get("salePrice", 0)), "original_price": float(item.get("normalPrice", 0)),
            "discount_percent": int(float(item.get("savings", 0))),
            "is_free": float(item.get("salePrice", 0)) == 0,
            "url": f"https://store.steampowered.com/app/{app_id}",
            "image": f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",
            "match_score": 0,
        })
    return results


async def _search_epic_catalog_api(query: str, limit: int = 15) -> list[dict]:
    gql = """query q($k: String!, $c: Int) { Catalog { catalogSearch(criteria: {keywords: $k, count: $c, sortBy: "relevance"}) { elements { title productSlug keyImages { type url } price { totalPrice { originalPrice discountPrice currencyCode } } urlMappings { pageSlug } } } } }"""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://store.epicgames.com/graphql",
                              json={"query": gql, "variables": {"k": query, "c": limit}},
                              headers={"Content-Type": "application/json"}, timeout=12) as r:
                data = await r.json()
    except Exception:
        return await _search_epic_alt(query, limit)
    try:
        elements = data["data"]["Catalog"]["catalogSearch"]["elements"]
    except Exception:
        return await _search_epic_alt(query, limit)
    results = []
    for item in elements:
        try:
            title = item.get("title", "")
            if not title:
                continue
            slug = item.get("productSlug")
            if not slug:
                mappings = item.get("urlMappings", [])
                slug = mappings[0].get("pageSlug", "") if mappings else ""
            if not slug:
                continue
            tp = item.get("price", {}).get("totalPrice", {})
            oc, dc = tp.get("originalPrice", 0), tp.get("discountPrice", 0)
            image = None
            for img in item.get("keyImages", []):
                if img.get("type") in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail"):
                    image = img.get("url")
                    if image:
                        break
            results.append({
                "title": title, "store": "Epic Games",
                "price": (dc / 100) if dc else 0, "original_price": (oc / 100) if oc else 0,
                "discount_percent": int((1 - dc / oc) * 100) if oc > 0 and dc < oc else 0,
                "is_free": dc == 0 and oc > 0,
                "url": f"https://store.epicgames.com/p/{slug}", "image": image or "", "match_score": 0,
            })
        except Exception:
            continue
    if not results:
        results = await _search_epic_alt(query, limit)
    return results


async def _search_epic_alt(query: str, limit: int = 15) -> list[dict]:
    gql = """query q($k: String, $c: Int) { Catalog { catalogOffers(criteria: {keyword: $k, count: $c, sortBy: "relevance"}) { elements { title productSlug keyImages { type url } price { totalPrice { originalPrice discountPrice currencyCode } } urlMappings { pageSlug } } } } }"""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://store-site-backend-static-ipv4.ak.epicgames.com/graphql",
                              json={"query": gql, "variables": {"k": query, "c": limit}},
                              headers={"Content-Type": "application/json"}, timeout=12) as r:
                data = await r.json()
    except Exception:
        return []
    try:
        elements = data["data"]["Catalog"]["catalogOffers"]["elements"]
    except Exception:
        return []
    results = []
    for item in elements:
        try:
            title = item.get("title", "")
            if not title:
                continue
            slug = item.get("productSlug")
            if not slug:
                mappings = item.get("urlMappings", [])
                slug = mappings[0].get("pageSlug", "") if mappings else ""
            if not slug:
                continue
            tp = item.get("price", {}).get("totalPrice", {})
            oc, dc = tp.get("originalPrice", 0), tp.get("discountPrice", 0)
            image = None
            for img in item.get("keyImages", []):
                if img.get("type") in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail"):
                    image = img.get("url")
                    if image:
                        break
            results.append({
                "title": title, "store": "Epic Games",
                "price": (dc / 100) if dc else 0, "original_price": (oc / 100) if oc else 0,
                "discount_percent": int((1 - dc / oc) * 100) if oc > 0 and dc < oc else 0,
                "is_free": dc == 0 and oc > 0,
                "url": f"https://store.epicgames.com/p/{slug}", "image": image or "", "match_score": 0,
            })
        except Exception:
            continue
    return results


async def search_by_exact_prefix(query: str) -> list[dict]:
    q = query.lower().strip()
    games = await get_all_deals_for_search()
    results = []
    seen = set()
    for game in games:
        key = f"{game['title']}|{game['store']}"
        if key in seen:
            continue
        tl = game["title"].lower()
        _, tr = normalize_title(game["title"])
        if tl.startswith(q) or tr.startswith(q):
            results.append(game)
            seen.add(key)
    return results[:20]