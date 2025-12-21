from aiogram import F
from aiogram.filters import Command
from database.database import get_db
from handlers import router
from services import SubscriptionService
from keyboards import get_main_keyboard, get_notification_days_keyboard
from database.models import User


# Обработчик команды /notify
@router.message(Command("notify"))
@router.message(F.text == "Настройки")
async def cmd_notify(message):
    """Обработчик команды /notify"""
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    current_days = user.notification_days
    response = (
        f"""*Настройки уведомлений*

Сейчас вы получаете уведомления за *{current_days}* дня до платежа.
Выберите, за сколько дней вы хотите получать уведомления:"""
    )
    await message.answer(response, parse_mode="Markdown",
                         reply_markup=get_notification_days_keyboard())


# Обработка выбора дней уведомления
@router.callback_query(F.data.startswith("notify_"))
async def process_notification_days(callback):
    """Обработка выбора дней уведомления"""
    days = int(callback.data.split("_")[1])
    db = next(get_db())
    success = SubscriptionService.set_notification_days(db, callback.from_user.id, days)

    if success:
        if days == 0:
            response = "*Уведомления отключены.*\n" \
                       "Вы не будете получать напоминания о платежах."
        else:
            response = f"*Уведомления настроены.*\n" \
                       f"Вы будете получать уведомления за {days} дня до платежа."

        await callback.message.edit_text(response, parse_mode="Markdown")
        await callback.message.answer("Настройки сохранены.", reply_markup=get_main_keyboard())
    else:
        await callback.message.answer("Произошла ошибка при обновлении настроек.",
                                      reply_markup=get_main_keyboard())
