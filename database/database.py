from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from config import config
from database.models import Base, Category


class Database:
    def __init__(self) -> None:
        self.database_url: str = config.DATABASE_URL
        self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False},
                                    echo=False, pool_pre_ping=True)
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine))

    def init_db(self) -> None:
        """Инициализация базы данных - создание всех таблиц"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("База данных инициализирована")
            self._create_default_categories()
        except SQLAlchemyError as e:
            print(f"Ошибка при инициализации базы данных: {e}")
            raise

    def _create_default_categories(self) -> None:
        """Создание категорий по умолчанию"""
        session = self.SessionLocal()
        try:
            existing_categories = session.query(Category).all()
            if existing_categories:
                return

            for cat_data in config.DEFAULT_CATEGORIES:
                category = Category(
                    name=cat_data["name"],
                    emoji=cat_data.get("emoji", ""),
                    is_default=True
                )
                session.add(category)

            session.commit()
            print("Категории по умолчанию созданы")
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Ошибка при создании категорий: {e}")
        finally:
            session.close()

    def get_session(self):
        """Получение сессии базы данных"""
        return self.SessionLocal()


db = Database()


def init_database():
    """Инициализация базы данных при запуске"""
    db.init_db()


def get_db():
    """Генератор сессий для использования в зависимостях"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
