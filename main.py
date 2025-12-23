import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import init_database
from handlers import router
from scheduler import NotificationScheduler

# Логи
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Основная функция запуска бота
async def main():
    """Основная функция запуска бота"""
    logger.info("Инициализация базы данных...")
    try:
        init_database()
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return

    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    scheduler = NotificationScheduler(bot)
    scheduler.start()

    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот завершил работу")


if __name__ == "__main__":
    if not config.BOT_TOKEN:
        print("Ошибка: BOT_TOKEN не найден в .env файле. Создайте файл .env и добавьте токен")
        exit(1)

    asyncio.run(main())
