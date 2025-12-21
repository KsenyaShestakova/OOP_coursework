from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import re

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.database import get_db
from phrases import FIRST_MESSAGE, HELP_TEXT
from services import SubscriptionService
from keyboards import get_main_keyboard, get_cancel_keyboard, get_categories_keyboard, \
    get_billing_period_keyboard, get_notification_days_keyboard
from database.models import User, Category

router = Router()


class EditSubscription(StatesGroup):
    waiting_for_period = State()
    waiting_for_category = State()
    waiting_for_field = State()
    waiting_for_value = State()


# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message):
    """Обработчик команды /start"""
    db = next(get_db())

    SubscriptionService.get_or_create_user(
        db,
        message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    await message.answer(FIRST_MESSAGE, parse_mode="Markdown", reply_markup=get_main_keyboard())


# Обработчик команды /help
@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def cmd_help(message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT, parse_mode="Markdown")


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
            next_payment = sub.next_payment_date.strftime("%d.%m.%Y") if sub.next_payment_date else "—"

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
            f"""*{sub.name}*\n
            {sub.price:.2f} {sub.currency}\n
            {sub.next_payment_date.strftime('%d.%m.%Y')} 
            ({days_until} {days_text})\n
            {category_name}\n\n"""
        )
    await message.answer(response, parse_mode="Markdown")
    db.close()


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


# Обработчик команды /subscription с параметрами
@router.message(Command("subscription"))
async def cmd_subscription_full(message):
    """Обработчик команды /subscription с параметрами"""
    text = message.text.strip()
    pattern = r'^/subscription\s+добавить\s+"([^"]+)"\s+(\d+(?:\.\d+)?)\s+(\d+)$'
    match = re.match(pattern, text)

    if not match:
        await message.answer(
            "Неправильный формат команды.\n\n"
            "Правильный формат:\n"
            '`/subscription добавить "Название" цена день`\n\n'
            "Пример:\n"
            '`/subscription добавить "Яндекс.Плюс" 399 25`',
            parse_mode="Markdown"
        )
        return

    name = match.group(1)
    price = float(match.group(2))
    day = int(match.group(3))

    if day < 1 or day > 31:
        await message.answer("День должен быть от 1 до 31.")
        return

    db = next(get_db())

    try:
        subscription = SubscriptionService.add_subscription(db, message.from_user.id,
                                                            name, price, day)

        await message.answer(
            f"""Подписка *{name}* успешно добавлена!\n\n
            Цена: {price:.2f} RUB\n
            День оплаты: {day}-е число\n
            Следующий платеж: {subscription.next_payment_date.strftime('%d.%m.%Y')}""",
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.answer(f"Ошибка при добавлении подписки: {str(e)}")


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


# Обработчик отмены
@router.message(F.text == "Отмена")
async def cmd_cancel(message, state):
    """Обработчик отмены"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=get_main_keyboard())
        return

    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_keyboard())


# Начало редактирования подписки
@router.callback_query(F.data.startswith("edit_"))
async def start_edit_subscription(callback, state):
    """Начало редактирования подписки"""
    subscription_id = int(callback.data.split("_")[1])

    await state.update_data(subscription_id=subscription_id)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Название", callback_data=f"edit_field_name"))
    builder.add(InlineKeyboardButton(text="Цену", callback_data=f"edit_field_price"))
    builder.add(InlineKeyboardButton(text="День платежа", callback_data=f"edit_field_day"))
    builder.add(InlineKeyboardButton(text="Периодичность", callback_data=f"edit_field_period"))
    builder.add(InlineKeyboardButton(text="Категорию", callback_data=f"edit_field_category"))
    builder.add(InlineKeyboardButton(text="Отмена", callback_data=f"edit_cancel"))
    builder.adjust(2)

    await callback.message.edit_text(
        "Что вы хотите изменить в этой подписке?",
        reply_markup=builder.as_markup()
    )


# Выбор поля для редактирования
@router.callback_query(F.data.startswith("edit_field_"))
async def select_edit_field(callback, state):
    """Выбор поля для редактирования"""
    field = callback.data.split("_")[2]
    await state.update_data(edit_field=field)

    if field == "name":
        await callback.message.edit_text("Введите новое название подписки:",
                                         reply_markup=get_cancel_keyboard())
        await state.set_state(EditSubscription.waiting_for_value)

    elif field == "price":
        await callback.message.edit_text(
            "Введите новую стоимость подписки (число, например: 399 или 1999.50):",
            reply_markup=get_cancel_keyboard())
        await state.set_state(EditSubscription.waiting_for_value)

    elif field == "day":
        await callback.message.edit_text(
            "Введите новый день месяца для оплаты (число от 1 до 31):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EditSubscription.waiting_for_value)

    elif field == "period":
        await callback.message.edit_text(
            "Выберите новую периодичность оплаты:",
            parse_mode="Markdown",
            reply_markup=get_billing_period_keyboard()
        )
        await state.set_state(EditSubscription.waiting_for_period)

    elif field == "category":
        db = next(get_db())
        categories = SubscriptionService.get_categories(db)
        await callback.message.edit_text(
            "Выберите новую категорию подписки:",
            parse_mode="Markdown"
        )
        await callback.message.edit_reply_markup(reply_markup=get_categories_keyboard(categories))
        await state.set_state(EditSubscription.waiting_for_category)


# Обработка нового значения для редактирования
@router.message(EditSubscription.waiting_for_value)
async def process_edit_value(message, state):
    """Обработка нового значения при редактировании"""
    data = await state.get_data()
    subscription_id = data.get('subscription_id')
    field = data.get('edit_field')

    if not subscription_id or not field:
        await message.answer("Ошибка: данные не найдены", reply_markup=get_main_keyboard())
        await state.clear()
        return

    if message.text == "Отмена":
        await state.clear()
        await message.answer("Редактирование отменено", reply_markup=get_main_keyboard())
        return

    db = next(get_db())
    update_data = {}

    try:
        if field == "name":
            if len(message.text) > 100:
                await message.answer(
                    "Название слишком длинное. Максимум 100 символов. Введите снова:")
                return
            update_data = {"name": message.text}

        elif field == "price":
            try:
                price = float(message.text.replace(',', '.'))
                if price <= 0:
                    await message.answer("Стоимость должна быть больше 0. Введите снова:")
                    return
                update_data = {"price": price}
            except ValueError:
                await message.answer("Пожалуйста, введите число (например: 399 или 1999.50):")
                return

        elif field == "day":
            try:
                day = int(message.text)
                if day < 1 or day > 31:
                    await message.answer("День должен быть от 1 до 31. Введите снова:")
                    return
                update_data = {"payment_day": day}
            except ValueError:
                await message.answer("Пожалуйста, введите число от 1 до 31:")
                return

        updated = SubscriptionService.update_subscription(
            db, subscription_id, message.from_user.id, **update_data
        )

        if updated:
            await message.answer(
                f"Подписка успешно обновлена!\n"
                f"Изменено поле: {field}\n"
                f"Новое значение: {message.text}",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer("Не удалось обновить подписку", reply_markup=get_main_keyboard())

    except Exception as e:
        await message.answer(f"Ошибка при обновлении: {str(e)}", reply_markup=get_main_keyboard())

    await state.clear()


# Обработка нового периода при редактировании
@router.callback_query(EditSubscription.waiting_for_period, F.data.startswith("period_"))
async def process_edit_period(callback, state):
    """Обработка нового периода при редактировании"""
    period = callback.data.split("_")[1]
    data = await state.get_data()
    subscription_id = data.get('subscription_id')

    if not subscription_id:
        await callback.answer("Ошибка: данные не найдены")
        return

    db = next(get_db())

    try:
        updated = SubscriptionService.update_subscription(
            db, subscription_id, callback.from_user.id, billing_period=period
        )

        if updated:
            period_names = {
                "monthly": "ежемесячно",
                "yearly": "ежегодно",
                "weekly": "еженедельно"
            }

            await callback.message.edit_text(
                f"Подписка успешно обновлена!\n"
                f"Изменена периодичность на: {period_names.get(period, period)}"
            )

            await callback.message.answer(
                "Что вы хотите сделать дальше?",
                reply_markup=get_main_keyboard()
            )
        else:
            await callback.message.answer("Не удалось обновить подписку",
                                          reply_markup=get_main_keyboard())

    except Exception as e:
        await callback.message.answer(f"Ошибка при обновлении: {str(e)}",
                                      reply_markup=get_main_keyboard())

    await state.clear()


# Обработка новой категории при редактировании
@router.callback_query(EditSubscription.waiting_for_category, F.data.startswith("category_"))
async def process_edit_category(callback, state):
    """Обработка новой категории при редактировании"""
    category_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    subscription_id = data.get('subscription_id')

    if not subscription_id:
        await callback.answer("Ошибка: данные не найдены")
        return

    db = next(get_db())

    try:
        updated = SubscriptionService.update_subscription(
            db, subscription_id, callback.from_user.id, category_id=category_id
        )

        if updated:
            category = db.query(Category).filter(Category.id == category_id).first()
            category_name = category.name if category else "Без категории"

            await callback.message.edit_text(
                f"Подписка успешно обновлена!\n"
                f"Новая категория: {category_name}"
            )

            await callback.message.answer(
                "Что вы хотите сделать дальше?",
                reply_markup=get_main_keyboard()
            )
        else:
            await callback.message.answer("Не удалось обновить подписку",
                                          reply_markup=get_main_keyboard())

    except Exception as e:
        await callback.message.answer(f"Ошибка при обновлении: {str(e)}",
                                      reply_markup=get_main_keyboard())

    await state.clear()


# Отмена редактирования
@router.callback_query(F.data == "edit_cancel")
async def cancel_edit(callback, state):
    """Отмена редактирования"""
    await state.clear()
    await callback.message.edit_text("Редактирование отменено")
    await callback.message.answer("Что вы хотите сделать дальше?", reply_markup=get_main_keyboard())


# Обработчик команды /edit
@router.message(F.text == "Редактировать")
@router.message(Command("edit"))
async def cmd_edit(message):
    """Обработчик команды /edit"""
    try:
        parts = message.text.split()

        if len(parts) < 2:
            await message.answer(
                "Использование: /edit <ID_подписки>\n"
                "Например: /edit 1\n\n"
                "Или: /edit <ID_подписки> <поле> <значение>\n"
                "Например: /edit 1 цена 499"
            )
            return

        subscription_id = int(parts[1])

        if len(parts) == 2:
            db = next(get_db())
            subscription = SubscriptionService.get_subscription_by_id(db, subscription_id,
                                                                      message.from_user.id)

            if not subscription:
                await message.answer("Подписка не найдена")
                return

            category_name = subscription.category.name if subscription.category else "Без категории"
            next_payment = subscription.next_payment_date.strftime("%d.%m.%Y")
            status = "Активна" if subscription.is_active else "Приостановлена"

            response = (
                f"*Информация о подписке:*\n\n"
                f"ID: {subscription.id}\n"
                f"Название: {subscription.name}\n"
                f"Стоимость: {subscription.price:.2f} {subscription.currency}\n"
                f"День платежа: {subscription.payment_day}-е число\n"
                f"Периодичность: {subscription.billing_period}\n"
                f"Категория: {category_name}\n"
                f"Следующий платеж: {next_payment}\n"
                f"Статус: {status}\n\n"
                f"Чтобы изменить:\n"
                f"/edit {subscription.id} название 'Новое название'\n"
                f"/edit {subscription.id} цена 499\n"
                f"/edit {subscription.id} день 15"
            )

            await message.answer(response, parse_mode="Markdown")
            return

        if len(parts) >= 4:
            field = parts[2].lower()
            value = " ".join(parts[3:])

            db = next(get_db())

            if field in ["название", "name"]:
                update_data = {"name": value}
            elif field in ["цена", "price", "стоимость"]:
                try:
                    price = float(value.replace(',', '.'))
                    if price <= 0:
                        await message.answer("Стоимость должна быть больше 0")
                        return
                    update_data = {"price": price}
                except ValueError:
                    await message.answer("Неверный формат цены. Используйте число")
                    return
            elif field in ["день", "day"]:
                try:
                    day = int(value)
                    if day < 1 or day > 31:
                        await message.answer("День должен быть от 1 до 31")
                        return
                    update_data = {"payment_day": day}
                except ValueError:
                    await message.answer("Неверный формат дня. Используйте число от 1 до 31")
                    return
            else:
                await message.answer(
                    "Неизвестное поле. Доступные поля:\n"
                    "- название (name)\n"
                    "- цена (price)\n"
                    "- день (day)"
                )
                return

            updated = SubscriptionService.update_subscription(
                db, subscription_id, message.from_user.id, **update_data
            )

            if updated:
                await message.answer(f"Подписка успешно обновлена!")
            else:
                await message.answer("Не удалось обновить подписку")

    except ValueError:
        await message.answer("Неверный формат ID. Используйте число")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


# Обработчик команды /toggle (Приостановка/возобновление подписки)
@router.message(F.text == "Приостановка/возобновление")
@router.message(Command("toggle"))
async def cmd_toggle(message):
    """Приостановка/возобновление подписки"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /toggle <ID_подписки>")
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


# Обработчик команды /delete (Удаление подписки)
@router.message(F.text == "Удалить")
@router.message(Command("delete"))
async def cmd_delete(message):
    """Удаление подписки"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer(
                "Использование: /delete <ID_подписки>\n\n"
                "Пример: /delete 1\n\n"
                "Список подписок: /list"
            )
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
