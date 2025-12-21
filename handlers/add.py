from aiogram.fsm.state import StatesGroup

from phrases import ADD_TEXT
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from database.database import get_db
from services import SubscriptionService
from keyboards import get_main_keyboard, get_cancel_keyboard, get_categories_keyboard, \
    get_billing_period_keyboard
from database.models import Category
from handlers import router


class AddSubscription(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_day = State()
    waiting_for_period = State()
    waiting_for_category = State()


# Обработчик команды /add
@router.message(Command("add"))
@router.message(F.text == "Добавить подписку")
async def cmd_add(message, state):
    """Обработчик команды /add"""
    await message.answer(
        ADD_TEXT,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AddSubscription.waiting_for_name)


# Обработка названия подписки
@router.message(AddSubscription.waiting_for_name)
async def process_subscription_name(message, state):
    """Обработка названия подписки"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer(
            "Добавление отменено",
            reply_markup=get_main_keyboard()
        )
        return

    if len(message.text) > 100:
        await message.answer(
            "Название слишком длинное. Максимум 100 символов. Введите название снова:")
        return

    await state.update_data(name=message.text)

    await message.answer(
        f"Название: *{message.text}*\n\n"
        "Теперь введите стоимость подписки (число, например: 399 или 1999.50):",
        parse_mode="Markdown"
    )
    await state.set_state(AddSubscription.waiting_for_price)


# Обработка стоимости подписки
@router.message(AddSubscription.waiting_for_price)
async def process_subscription_price(message, state):
    """Обработка стоимости подписки"""
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0:
            await message.answer(
                "Стоимость должна быть больше 0. Введите снова:"
            )
            return

        await state.update_data(price=price)

        await message.answer(
            f"Стоимость: *{price:.2f} RUB*\n\n"
            "Введите день месяца для оплаты (число от 1 до 31):",
            parse_mode="Markdown"
        )
        await state.set_state(AddSubscription.waiting_for_day)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число (например: 399 или 1999.50):"
        )


# Обработка дня платежа
@router.message(AddSubscription.waiting_for_day)
async def process_payment_day(message, state):
    """Обработка дня платежа"""
    try:
        day = int(message.text)
        if day < 1 or day > 31:
            await message.answer(
                "День должен быть от 1 до 31. Введите снова:"
            )
            return

        await state.update_data(day=day)

        await message.answer(
            f"День платежа: *{day}-е число*\n\n"
            "Выберите периодичность оплаты:",
            parse_mode="Markdown",
            reply_markup=get_billing_period_keyboard()
        )
        await state.set_state(AddSubscription.waiting_for_period)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число от 1 до 31:"
        )


# Обработка выбора периодичности
@router.callback_query(AddSubscription.waiting_for_period, F.data.startswith("period_"))
async def process_billing_period(callback, state):
    """Обработка выбора периодичности"""
    period = callback.data.split("_")[1]
    period_names = {
        "monthly": "ежемесячно",
        "yearly": "ежегодно",
        "weekly": "еженедельно"
    }

    await state.update_data(billing_period=period)
    db = next(get_db())
    categories = SubscriptionService.get_categories(db)

    await callback.message.edit_text(
        f"Периодичность: *{period_names.get(period, period)}*\n\nВыберите категорию подписки:",
        parse_mode="Markdown"
    )
    await callback.message.edit_reply_markup(reply_markup=get_categories_keyboard(categories))
    await state.set_state(AddSubscription.waiting_for_category)
    db.close()


# Обработка выбора категории
@router.callback_query(AddSubscription.waiting_for_category, F.data.startswith("category_"))
async def process_category(callback, state):
    """Обработка выбора категории"""
    category_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    db = next(get_db())
    try:
        subscription = SubscriptionService.add_subscription(
            db,
            callback.from_user.id,
            data['name'],
            data['price'],
            data['day'],
            data['billing_period'],
            category_id
        )

        category = db.query(Category).filter(Category.id == category_id).first()
        category_name = category.name if category else "Без категории"
        success_text = (
            f"""*Подписка успешно добавлена!*

            *Название:* {subscription.name}
            *Стоимость:* {subscription.price:.2f} {subscription.currency}
            *День платежа:* {subscription.payment_day}-е число
            *Периодичность:* {data['billing_period']}
            *Категория:* {category_name}
            *Следующий платеж:* {subscription.next_payment_date.strftime('%d.%m.%Y')}

            "Подписка будет отображаться в списке ваших подписок."""
        )

        await callback.message.edit_text(
            success_text,
            parse_mode="Markdown"
        )

        await state.clear()
        await callback.message.answer("Что вы хотите сделать дальше?",
                                      reply_markup=get_main_keyboard())

    except Exception as e:
        await callback.message.answer(f"Ошибка при добавлении подписки: {str(e)}",
                                      reply_markup=get_main_keyboard())
        await state.clear()
    db.close()