from aiogram.filters import Command
from database.database import get_db
from handlers import router
from services import SubscriptionService


# Обработчик команды /category
@router.message(Command("category"))
async def cmd_category(message):
    """Обработчик команды /category"""
    db = next(get_db())
    categories = SubscriptionService.get_categories(db)

    if not categories:
        await message.answer("Категории не найдены.")
        return

    categories_text = "*Доступные категории:*\n\n"
    for category in categories:
        categories_text += f"{category.emoji or ''} {category.name}\n"

    categories_text += "\nЧтобы установить категорию для подписки, "
    categories_text += "отредактируйте подписку через список подписок."

    await message.answer(categories_text, parse_mode="Markdown")