from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.database import get_db
from handlers import router
from services import SubscriptionService
from keyboards import get_main_keyboard, get_cancel_keyboard, get_categories_keyboard, \
    get_billing_period_keyboard
from database.models import Category


class EditSubscription(StatesGroup):
    waiting_for_period = State()
    waiting_for_category = State()
    waiting_for_field = State()
    waiting_for_value = State()


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

    await callback.message.edit_text("Что вы хотите изменить в этой подписке?",
                                     reply_markup=builder.as_markup())


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
        await callback.message.edit_text("Введите новый день месяца для оплаты (число от 1 до 31):",
                                         reply_markup=get_cancel_keyboard())
        await state.set_state(EditSubscription.waiting_for_value)

    elif field == "period":
        await callback.message.edit_text("Выберите новую периодичность оплаты:",
                                         parse_mode="Markdown",
                                         reply_markup=get_billing_period_keyboard())
        await state.set_state(EditSubscription.waiting_for_period)

    elif field == "category":
        db = next(get_db())
        try:
            categories = SubscriptionService.get_categories(db)
            await callback.message.edit_text("Выберите новую категорию подписки:",
                                             parse_mode="Markdown")
            await callback.message.edit_reply_markup(
                reply_markup=get_categories_keyboard(categories))
            await state.set_state(EditSubscription.waiting_for_category)
        finally:
            db.close()


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
    try:
        update_data = {}

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

        updated = SubscriptionService.update_subscription(db, subscription_id, message.from_user.id,
                                                          **update_data)

        if updated:
            await message.answer(
                f"""Подписка успешно обновлена!
Изменено поле: {field}
Новое значение: {message.text}""",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer("Не удалось обновить подписку", reply_markup=get_main_keyboard())

    except Exception as e:
        await message.answer(f"Ошибка при обновлении: {str(e)}", reply_markup=get_main_keyboard())
    finally:
        db.close()

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
        updated = SubscriptionService.update_subscription(db, subscription_id,
                                                          callback.from_user.id,
                                                          billing_period=period)

        if updated:
            period_names = {
                "monthly": "ежемесячно",
                "yearly": "ежегодно",
                "weekly": "еженедельно"
            }

            await callback.message.edit_text(
                f"""Подписка успешно обновлена!
Изменена периодичность на: {period_names.get(period, period)}"""
            )

            await callback.message.answer("Что вы хотите сделать дальше?",
                                          reply_markup=get_main_keyboard())
        else:
            await callback.message.answer("Не удалось обновить подписку",
                                          reply_markup=get_main_keyboard())

    except Exception as e:
        await callback.message.answer(f"Ошибка при обновлении: {str(e)}",
                                      reply_markup=get_main_keyboard())
    finally:
        db.close()

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
        updated = SubscriptionService.update_subscription(db, subscription_id,
                                                          callback.from_user.id,
                                                          category_id=category_id)

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
    finally:
        db.close()

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
            try:
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
            finally:
                db.close()
            return

        if len(parts) >= 4:
            field = parts[2].lower()
            value = " ".join(parts[3:])

            db = next(get_db())
            try:
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

                updated = SubscriptionService.update_subscription(db, subscription_id,
                                                                  message.from_user.id,
                                                                  **update_data)

                if updated:
                    await message.answer(f"Подписка успешно обновлена!")
                else:
                    await message.answer("Не удалось обновить подписку")
            finally:
                db.close()

    except ValueError:
        await message.answer("Неверный формат ID. Используйте число")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
