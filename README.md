# WTF Steam Bot

Telegram бот для отслеживания:

* 🔥 лучших скидок Steam
* 🎁 бесплатных раздач Epic Games
* 🎁 Steam халявы
* 🔥 скидок Epic Games

---

# Возможности

✅ Проверка подписки на канал
✅ Листание карточек
✅ Картинки игр
✅ Anti-trash фильтр
✅ Кэширование API
✅ Асинхронная работа
✅ Красивый интерфейс

---

# Установка

## 1. Установить Python 3.11+

Скачать:
https://www.python.org/downloads/

---

## 2. Создать виртуальное окружение

```bash
python -m venv venv
```

---

## 3. Активировать venv

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

---

## 4. Установить зависимости

```bash
pip install -r requirements.txt
```

---

## 5. Указать токен бота

Открыть:

config.py

и вставить:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN"
```

---

# Запуск

```bash
python bot.py
```

---

# Создание Telegram бота

1. Открыть @BotFather
2. Написать:

```txt
/newbot
```

3. Ввести имя бота
4. Получить TOKEN

---

# Проверка подписки

Добавьте бота в канал:

@WTF_steam

И выдайте права:

✅ Admin
✅ Invite Users
✅ Delete Messages

---

# Команды

/start

---

# Структура

services/ — API Steam/Epic
handlers/ — Telegram callbacks
utils.py — форматирование
filters.py — анти-мусор
cache.py — кэш

---

# Автор

1zhur1
