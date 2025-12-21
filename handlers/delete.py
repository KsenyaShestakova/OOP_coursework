from aiogram import F
from aiogram.filters import Command
from database.database import get_db
from handlers import router
from services import SubscriptionService


# Обработчик команды /delete (Удаление подписки)
@router.message(F.text == "Удалить")
@router.message(Command("delete"))
async def cmd_delete(message):
    """Удаление подписки"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer(
                "Использование: /delete <ID_подписки>\n"
                "Пример: /delete 1\n"
                "Список подписок: /list")
            return

        subscription_id = int(parts[1])
        db = next(get_db())

        success = SubscriptionService.delete_subscription(db, subscription_id, message.from_user.id)

        if success:
            await message.answer(f"Подписка ID:{subscription_id} удалена")
        else:
            await message.answer(f"Подписка не найдена")

    except ValueError:
        await message.answer("Неверный ID. Используйте число")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
