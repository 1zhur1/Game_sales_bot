import time

from config import CACHE_TTL

cache = {}


def get_cache(key):

    if key not in cache:
        return None

    item = cache[key]

    if time.time() - item["time"] > CACHE_TTL:
        return None

    return item["data"]


def set_cache(key, data):

    cache[key] = {
        "time": time.time(),
        "data": data,
    }