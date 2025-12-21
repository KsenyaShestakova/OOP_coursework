from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# Главная клавиатура
def get_main_keyboard():
    """Главная клавиатура"""
    buttons = [
        "Мои подписки",
        "Добавить подписку",
        "Ближайшие платежи",
        "Настройки",
        "Помощь",
        "Приостановка/возобновление",
        "Редактировать",
        "Удалить"
    ]

    builder = ReplyKeyboardBuilder()
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


# Клавиатура для отмены
def get_cancel_keyboard():
    """Клавиатура для отмены"""
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True)


# Клавиатура для выбора категории
def get_categories_keyboard(categories):
    """Клавиатура для выбора категории"""
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.add(InlineKeyboardButton(text=f"{category.emoji or ''} {category.name}",
                                         callback_data=f"category_{category.id}"))
    builder.adjust(2)
    return builder.as_markup()


# Клавиатура для выбора периода оплаты
def get_billing_period_keyboard():
    """Клавиатура для выбора периода оплаты"""
    periods = [("Ежемесячно", "monthly"), ("Ежегодно", "yearly"), ("Еженедельно", "weekly")]

    builder = InlineKeyboardBuilder()
    for text, period in periods:
        builder.add(InlineKeyboardButton(text=text, callback_data=f"period_{period}"))
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура настроек
def get_settings_keyboard():
    """Клавиатура настроек"""
    settings = [("Уведомления", "notifications"), ("Категории", "categories"),
                ("Очистить данные", "clear_data")]

    builder = InlineKeyboardBuilder()
    for text, action in settings:
        builder.add(InlineKeyboardButton(text=text, callback_data=f"settings_{action}"))
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура для выбора дней уведомления
def get_notification_days_keyboard():
    """Клавиатура для выбора дней уведомления"""
    days_options = [("Отключить", "0"), ("1 день", "1"), ("3 дня", "3"), ("7 дней", "7")]

    builder = InlineKeyboardBuilder()
    for text, days in days_options:
        builder.add(InlineKeyboardButton(text=text, callback_data=f"notify_{days}"))
    builder.adjust(2)
    return builder.as_markup()


# Клавиатура подтверждения
def get_confirm_keyboard(action):
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Да", callback_data=f"confirm_{action}"))
    builder.add(InlineKeyboardButton(text="Нет", callback_data=f"cancel_{action}"))
    builder.adjust(2)
    return builder.as_markup()
