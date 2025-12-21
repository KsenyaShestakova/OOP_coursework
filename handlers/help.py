from aiogram import F
from aiogram.filters import Command
from handlers import router
from phrases import HELP_TEXT


# Обработчик команды /help
@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def cmd_help(message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT, parse_mode="Markdown")
