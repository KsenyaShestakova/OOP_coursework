from datetime import datetime

from aiogram import F
from aiogram.filters import Command
from database.database import get_db
from services import SubscriptionService
from handlers import router


# Обработчик команды /upcoming
@router.message(Command("upcoming"))
@router.message(F.text == "Ближайшие платежи")
async def cmd_upcoming(message):
    """Обработчик команды /upcoming"""
    db = next(get_db())
    upcoming = SubscriptionService.get_upcoming_payments(db, message.from_user.id, days_ahead=14)

    if not upcoming:
        await message.answer("В ближайшие 14 дней у вас нет предстоящих платежей",
                             parse_mode="Markdown")
        return

    response = "*Платежи в ближайшие 14 дней:*\n\n"
    today = datetime.now().date()

    for sub in upcoming:
        days_until = (sub.next_payment_date - today).days
        if days_until == 1:
            days_text = "день"
        elif 2 <= days_until <= 4:
            days_text = "дня"
        else:
            days_text = "дней"

        category_name = sub.category.name if sub.category else "Без категории"
        response += (
            f"""*{sub.name}*
{sub.price:.2f} {sub.currency}
{sub.next_payment_date.strftime('%d.%m.%Y')} 
({days_until} {days_text})
{category_name}\n\n"""
        )
    await message.answer(response, parse_mode="Markdown")
    db.close()
