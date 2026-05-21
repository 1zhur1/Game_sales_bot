import os

BOT_TOKEN = "8844414313:AAEj5XZ6g_URkRiF-vuNUQY6WoZG3HecXJA"

CHANNEL_USERNAME = "@WTF_steam"

# Интервал проверки новых скидок/халявы (в секундах)
NOTIFICATION_INTERVAL = 3600  # 1 час

# Интервал фонового мониторинга подписок (в секундах)
MONITOR_INTERVAL = 1800  # 30 минут

# Максимум сделок в одном уведомлении
MAX_NOTIFICATION_DEALS = 10

# Лимиты отображения в списках
DEALS_PAGE_SIZE = 100  # Показывать до 100 игр
DEALS_PER_PAGE = 5     # По 5 на страницу в пагинации

# Настройки кэша
CACHE_TTL = 3600  # 1 час

# Путь к БД
DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")

# Настройки поиска
FUZZY_SEARCH_THRESHOLD = 60  # Минимальный порог схожести для fuzzy search (0-100)