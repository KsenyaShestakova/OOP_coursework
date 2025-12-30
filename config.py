import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = "sqlite:///database/subscriptions.db"

    NOTIFICATION_HOUR = 15  # во сколько будут отправляться уведомления (24-часовой формат)

    # Категории по умолчанию
    DEFAULT_CATEGORIES = [
        {"name": "Развлечения"},
        {"name": "Музыка"},
        {"name": "Обучение"},
        {"name": "Игры"},
        {"name": "Связь"},
        {"name": "Дом"},
        {"name": "Спорт"},
        {"name": "Другое"}
    ]


config = Config()
