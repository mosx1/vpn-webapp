"""Общая настройка тестов.

db/models.py на импорте вызывает Base.metadata.create_all(engine), из-за чего
любой импорт моделей требует живую БД. Для юнит-тестов подменяем create_all
до импорта моделей, чтобы тесты не зависели от подключения.
"""

import sqlalchemy

sqlalchemy.MetaData.create_all = lambda self, *args, **kwargs: None
