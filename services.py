from datetime import date, timedelta
import calendar
from database.models import User, Subscription, Category


class SubscriptionService:
    # Получить пользователя или создать нового
    @staticmethod
    def get_or_create_user(session, telegram_id, **kwargs):
        """Получить пользователя или создать нового"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=kwargs.get('username'),
                first_name=kwargs.get('first_name'),
                last_name=kwargs.get('last_name'),
                notification_days=3
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    # Добавить новую подписку
    @staticmethod
    def add_subscription(session, user_id, name, price, payment_day,
                         billing_period="monthly", category_id=None,
                         description=None):
        """Добавить новую подписку"""
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            raise ValueError("Пользователь не найден")

        payment_day = max(1, min(31, payment_day))
        next_payment = SubscriptionService._calculate_next_payment_date(payment_day)
        subscription = Subscription(
            user_id=user.id,
            name=name,
            price=price,
            payment_day=payment_day,
            billing_period=billing_period,
            category_id=category_id,
            description=description,
            next_payment_date=next_payment
        )
        session.add(subscription)
        session.commit()
        session.refresh(subscription)
        return subscription

    # Рассчитать следующую дату платежа
    @staticmethod
    def _calculate_next_payment_date(payment_day):
        """Рассчитать следующую дату платежа"""
        today = date.today()
        _, days_in_month = calendar.monthrange(today.year, today.month)
        actual_day = min(payment_day, days_in_month)
        try:
            payment_date = date(today.year, today.month, actual_day)
        except ValueError:
            payment_date = date(today.year, today.month, days_in_month)

        if payment_date < today:
            if today.month == 12:
                next_year = today.year + 1
                next_month = 1
            else:
                next_year = today.year
                next_month = today.month + 1

            _, next_days_in_month = calendar.monthrange(next_year, next_month)
            actual_day = min(payment_day, next_days_in_month)
            payment_date = date(next_year, next_month, actual_day)
        return payment_date

    # Получить все подписки пользователя
    @staticmethod
    def get_user_subscriptions(session, telegram_id, active_only=True):
        """Получить все подписки пользователя"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []

        query = session.query(Subscription).filter(Subscription.user_id == user.id)
        if active_only:
            query = query.filter(Subscription.is_active == True)

        return query.order_by(Subscription.next_payment_date).all()

    # Получить подписку по ID
    @staticmethod
    def get_subscription_by_id(session, subscription_id, user_id):
        """Получить подписку по ID"""
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return None

        return session.query(Subscription).filter(Subscription.id == subscription_id,
                                                  Subscription.user_id == user.id).first()

    # Обновить подписку
    @staticmethod
    def update_subscription(session, subscription_id, user_id, **kwargs):
        """Обновить подписку"""
        subscription = SubscriptionService.get_subscription_by_id(session, subscription_id, user_id)

        if not subscription:
            return None

        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        if 'payment_day' in kwargs:
            subscription.next_payment_date = SubscriptionService._calculate_next_payment_date(subscription.payment_day)

        session.commit()
        session.refresh(subscription)

        return subscription

    # Удалить подписку
    @staticmethod
    def delete_subscription(session, subscription_id, user_id):
        """Удалить подписку"""
        subscription = SubscriptionService.get_subscription_by_id(session, subscription_id, user_id)

        if not subscription:
            return False

        session.delete(subscription)
        session.commit()
        return True

    # Включить/выключить подписку
    @staticmethod
    def toggle_subscription(session, subscription_id, user_id):
        """Включить/выключить подписку"""
        subscription = SubscriptionService.get_subscription_by_id(session, subscription_id, user_id)

        if not subscription:
            return None

        subscription.is_active = not subscription.is_active
        session.commit()
        session.refresh(subscription)
        return subscription

    # Получить ближайшие платежи
    @staticmethod
    def get_upcoming_payments(session, telegram_id, days_ahead=7):
        """Получить ближайшие платежи"""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []

        subscriptions = session.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True,
            Subscription.next_payment_date >= today,
            Subscription.next_payment_date <= end_date
        ).order_by(Subscription.next_payment_date).all()

        return subscriptions

    # Рассчитать суммы расходов
    @staticmethod
    def calculate_totals(session, telegram_id):
        """Рассчитать суммы расходов"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return {"monthly": 0.0, "yearly": 0.0}

        subscriptions = session.query(Subscription).filter(Subscription.user_id == user.id,
                                                           Subscription.is_active == True).all()
        monthly_total = 0.0
        yearly_total = 0.0
        for sub in subscriptions:
            if sub.billing_period == "monthly":
                monthly_total += sub.price
                yearly_total += sub.price * 12
            elif sub.billing_period == "yearly":
                monthly_total += sub.price / 12
                yearly_total += sub.price
            elif sub.billing_period == "weekly":
                monthly_total += sub.price * 4.33
                yearly_total += sub.price * 52

        return {"monthly": round(monthly_total, 2),
                "yearly": round(yearly_total, 2)}

    # Установить количество дней для уведомлений
    @staticmethod
    def set_notification_days(session, telegram_id, days):
        """Установить количество дней для уведомлений"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False

        user.notification_days = max(0, min(30, days))
        session.commit()
        return True

    # Получить все категории
    @staticmethod
    def get_categories(session):
        """Получить все категории"""
        return session.query(Category).order_by(Category.name).all()

    # Обновить даты следующих платежей для всех активных подписок
    @staticmethod
    def update_next_payment_dates(session):
        """Обновить даты следующих платежей для всех активных подписок"""
        today = date.today()
        subscriptions = session.query(Subscription).filter(Subscription.is_active == True,
                                                           Subscription.next_payment_date < today).all()

        for sub in subscriptions:
            next_date = sub.next_payment_date

            while next_date < today:
                if sub.billing_period == "monthly":
                    try:
                        next_date = date(next_date.year, next_date.month + 1, sub.payment_day)
                    except ValueError:
                        if next_date.month == 12:
                            next_year = next_date.year + 1
                            next_month = 1
                        else:
                            next_year = next_date.year
                            next_month = next_date.month + 1

                        _, days_in_month = calendar.monthrange(next_year, next_month)
                        actual_day = min(sub.payment_day, days_in_month)
                        next_date = date(next_year, next_month, actual_day)

                elif sub.billing_period == "yearly":
                    try:
                        next_date = date(next_date.year + 1, next_date.month, sub.payment_day)
                    except ValueError:
                        _, days_in_month = calendar.monthrange(next_date.year + 1, next_date.month)
                        actual_day = min(sub.payment_day, days_in_month)
                        next_date = date(next_date.year + 1, next_date.month, actual_day)

                elif sub.billing_period == "weekly":
                    next_date += timedelta(days=7)
            sub.next_payment_date = next_date
        session.commit()


class NotificationService:
    # Получить подписки, по которым нужно отправить уведомления
    @staticmethod
    def get_subscriptions_for_notification(session):
        """Получить подписки, по которым нужно отправить уведомления"""
        today = date.today()
        users = session.query(User).filter(User.notification_days > 0).all()
        subscriptions_to_notify = []

        for user in users:
            notify_date = today + timedelta(days=user.notification_days)
            subscriptions = session.query(Subscription).filter(Subscription.user_id == user.id,
                                                               Subscription.is_active == True,
                                                               Subscription.notifications_enabled == True,
                                                               Subscription.next_payment_date == notify_date).all()
            subscriptions_to_notify.extend(subscriptions)
        return subscriptions_to_notify

    # Форматировать сообщение для уведомления
    @staticmethod
    def format_notification_message(subscription):
        """Форматировать сообщение для уведомления"""
        today = date.today()
        days_until = (subscription.next_payment_date - today).days
        period_texts = {
            "monthly": "ежемесячная",
            "yearly": "ежегодная",
            "weekly": "еженедельная"
        }
        category_text = f"{subscription.category.name}" if subscription.category else ""
        return (
            f"*Напоминание о платеже*\n\n"
            f"*Подписка:* {subscription.name}\n"
            f"*Сумма:* {subscription.price} {subscription.currency}\n"
            f"*Дата платежа:* {subscription.next_payment_date.strftime('%d.%m.%Y')}\n"
            f"*Осталось дней:* {days_until}\n"
            f"*Период:* {period_texts.get(subscription.billing_period, subscription.billing_period)}\n"
            f"{category_text}\n\n"
            f"_Не забудьте оплатить вовремя!_"
        )
