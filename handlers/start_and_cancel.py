from aiogram import Router, F
from aiogram.filters import CommandStart
from database.database import get_db
from phrases import FIRST_MESSAGE
from services import SubscriptionService
from keyboards import get_main_keyboard

router = Router()


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
