from entities.exceptions import CacheError
from utils import log


LOGGER = None
CACHE = None


def init():
    global CACHE, LOGGER
    CACHE = {}
    LOGGER = log.get_logger("cache")


def keys():
    try:
        return CACHE.keys()
    except:
        LOGGER.warning("no cache keys")


def get(key):
    # fixme
    return None
    try:
        return CACHE[key]
    except KeyError:
        return None


def update(key, value):
    try:
        CACHE.update({key: value})
    except Exception as e:
        LOGGER.warning(f"cannot update cache, key={key}, CACHE={CACHE}, type(key)={type(key)}e={e}")


# fixme cannot delete cache
def delete(key=None, bulk=False):
    try:
        if not key:
            CACHE.keys()
            CACHE.clear()
        else:
            if bulk:
                delete_keys = set()
                for k in CACHE.keys():
                    if key in k:
                        delete_keys.add(k)

                for k in delete_keys:
                    CACHE.pop(k)
            else:
                CACHE.pop(key)
    except Exception as e:
        LOGGER.warning(f"cannot delete cache, key={key}, CACHE={CACHE}, e={e}")
