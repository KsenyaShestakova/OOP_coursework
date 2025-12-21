from aiogram import F
from aiogram.filters import Command
from database.database import get_db
from services import SubscriptionService
from keyboards import get_main_keyboard
from handlers import router


# Обработчик команды /list
@router.message(Command("list"))
@router.message(F.text == "Мои подписки")
async def cmd_list(message):
    """Обработчик команды /list"""
    db = next(get_db())
    subscriptions = SubscriptionService.get_user_subscriptions(db, message.from_user.id,
                                                               active_only=False)

    if not subscriptions:
        await message.answer("У вас пока нет активных подписок.\n"
                             "Добавьте первую с помощью /add или кнопки 'Добавить подписку'.",
                             reply_markup=get_main_keyboard())
        return

    active_subs = [sub for sub in subscriptions if sub.is_active]
    inactive_subs = [sub for sub in subscriptions if not sub.is_active]
    response = ""
    if active_subs:
        response += "*Активные подписки:*\n\n"
        total_monthly = 0
        total_yearly = 0

        for i, sub in enumerate(active_subs, 1):
            if sub.billing_period == "monthly":
                monthly_cost = sub.price
                yearly_cost = sub.price * 12
            elif sub.billing_period == "yearly":
                monthly_cost = sub.price / 12
                yearly_cost = sub.price
            elif sub.billing_period == "weekly":
                monthly_cost = sub.price * 4.33
                yearly_cost = sub.price * 52
            else:
                monthly_cost = sub.price
                yearly_cost = sub.price * 12

            total_monthly += monthly_cost
            total_yearly += yearly_cost

            category_name = sub.category.name if sub.category else "Без категории"
            next_payment = sub.next_payment_date.strftime("%d.%m.%Y")

            response += (
                f"""{i}. *{sub.name}* (ID: `{sub.id}`)
{sub.price:.2f} {sub.currency} ({sub.billing_period})
Следующий платеж: {next_payment}
Категория: {category_name}
В месяц: {monthly_cost:.2f} рублей\n\n"""
            )

        response += f"*Итого активных в месяц: {total_monthly:.2f} рублей*\n"
        response += f"*Итого активных в год: {total_yearly:.2f} рублей*\n\n"

    else:
        response += "*У вас нет активных подписок*\n\n"

    if inactive_subs:
        response += "*Неактивные подписки:*\n\n"

        for i, sub in enumerate(inactive_subs, 1):
            category_name = sub.category.name if sub.category else "Без категории"
            next_payment = sub.next_payment_date.strftime(
                "%d.%m.%Y") if sub.next_payment_date else "—"

            response += (
                f"""{i}. *{sub.name}* (ID: `{sub.id}`) [приостановлена]
{sub.price:.2f} {sub.currency} ({sub.billing_period})
Следующий платеж: {next_payment}
Категория: {category_name}\n"""
            )
    else:
        response += "*У вас нет неактивных подписок*\n\n"

    response += (
        """*Управление подписками:*
`/edit <ID>` - редактировать подписку
`/toggle <ID>` - приостановить/возобновить
`/delete <ID>` - удалить подписку

*Пример:* `/edit 1` - редактировать подписку с ID 1"""
)

    await message.answer(response, parse_mode="Markdown")