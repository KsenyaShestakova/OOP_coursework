from aiogram import F
from aiogram.filters import Command
from database.database import get_db
from handlers import router
from services import SubscriptionService


# Обработчик команды /toggle (Приостановка/возобновление подписки)
@router.message(F.text == "Приостановка/возобновление")
@router.message(Command("toggle"))
async def cmd_toggle(message):
    """Приостановка/возобновление подписки"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: `/toggle` <ID_подписки>")
            return

        subscription_id = int(parts[1])
        db = next(get_db())

        subscription = SubscriptionService.toggle_subscription(
            db, subscription_id, message.from_user.id
        )

        if subscription:
            status = "приостановлена" if not subscription.is_active else "возобновлена"
            await message.answer(f"Подписка успешно {status}!")
        else:
            await message.answer("Подписка не найдена")

    except ValueError:
        await message.answer("Неверный формат ID")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
