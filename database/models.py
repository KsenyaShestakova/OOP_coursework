from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    notification_days = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB')
    payment_day = Column(Integer, nullable=False)
    billing_period = Column(String(20), default='monthly')
    category_id = Column(Integer, ForeignKey('categories.id'))
    is_active = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(Date, default=date.today)
    next_payment_date = Column(Date, nullable=False)

    user = relationship("User", back_populates="subscriptions")
    category = relationship("Category", back_populates="subscriptions")


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    emoji = Column(String(10))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    subscriptions = relationship("Subscription", back_populates="category")


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    subscription = relationship("Subscription")
