"""Сайт семьи Akiyama — FastAPI внутри процесса бота (общая БД и Discord).

Содержит:
- app — create_app: сборка FastAPI-приложения
- session — HMAC-подпись cookie сессии
- oauth — Discord OAuth (identify+guilds) для входа стаффа
- online — кэш онлайна сервера (gta5masterlist.ru, публичный JSON)
- routes_public — страницы для всех: /, /roster, /vzp, /online, /gatherings
- routes_staff — панель стаффа: /staff, заявки и сборы
"""
