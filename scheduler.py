from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from database import get_db
from services import SubscriptionService, NotificationService
from config import config

logger = logging.getLogger(__name__)


class NotificationScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    # Запуск планировщика
    def start(self):
        """Запуск планировщика"""
        self.scheduler.add_job(self.send_daily_notifications,
                               CronTrigger(hour=config.NOTIFICATION_HOUR, minute=0),
                               id="daily_notifications")

        self.scheduler.add_job(self.update_payment_dates, CronTrigger(hour=0, minute=0),
                               id="update_payment_dates")
        self.scheduler.add_job(self.send_monthly_report, CronTrigger(day=1, hour=9, minute=0),
                               id="monthly_report")
        self.scheduler.start()
        logger.info("Планировщик уведомлений запущен")

    # Отправка ежедневных уведомлений
    async def send_daily_notifications(self):
        """Отправка ежедневных уведомлений"""
        logger.info("Отправка ежедневных уведомлений...")
        db = next(get_db())

        try:
            subscriptions = NotificationService.get_subscriptions_for_notification(db)

            if not subscriptions:
                logger.info("Нет подписок для уведомлений")
                return

            logger.info(f"Найдено {len(subscriptions)} подписок для уведомлений")

            for subscription in subscriptions:
                try:
                    message = NotificationService.format_notification_message(subscription)
                    await self.bot.send_message(chat_id=subscription.user.telegram_id, text=message,
                                                parse_mode="Markdown")
                    logger.info(
                        f"Уведомление отправлено пользователю {subscription.user.telegram_id}")

                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления: {e}")

        except Exception as e:
            logger.error(f"Ошибка при получении подписок для уведомлений: {e}")
        finally:
            db.close()

    # Обновление дат платежей
    async def update_payment_dates(self):
        """Обновление дат платежей"""
        logger.info("Обновление дат платежей...")
        db = next(get_db())
        try:
            SubscriptionService.update_next_payment_dates(db)
            logger.info("Даты платежей обновлены")
        except Exception as e:
            logger.error(f"Ошибка при обновлении дат платежей: {e}")
        finally:
            db.close()

    # Отправка ежемесячного отчета
    async def send_monthly_report(self):
        """Отправка ежемесячного отчета"""
        logger.info("Отправка ежемесячного отчета...")
        db = next(get_db())
        try:
            from database.models import User
            users = db.query(User).all()

            for user in users:
                try:
                    totals = SubscriptionService.calculate_totals(db, user.telegram_id)
                    if totals['monthly'] == 0:
                        continue

                    report = (
                        f"*Ежемесячный отчет по подпискам*\n\n"
                        f"*Расходы за месяц:* {totals['monthly']:.2f} RUB\n"
                        f"*Расходы за год:* {totals['yearly']:.2f} RUB\n\n"
                        f"Отчет за {datetime.now().strftime('%B %Y')}.\n"
                        "Используйте /stats для подробной статистики."
                    )

                    await self.bot.send_message(chat_id=user.telegram_id, text=report,
                                                parse_mode="Markdown")
                    logger.info(f"Ежемесячный отчет отправлен пользователю {user.telegram_id}")

                except Exception as e:
                    logger.error(f"Ошибка при отправке отчета пользователю {user.telegram_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка при отправке ежемесячного отчета: {e}")
        finally:
            db.close()

    # Остановка планировщика
    def shutdown(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Планировщик уведомлений остановлен")
