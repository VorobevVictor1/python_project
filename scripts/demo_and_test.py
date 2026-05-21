"""
Скрипт для генерации демо-данных и автопроверки рекомендательной системы.

Сценарий:
1. Создаёт 2 пользователей с перекрывающимися вкусами
2. Генерирует события чтений (оценки)
3. Запускает пересчёт рекомендаций
4. Проверяет, что рекомендации логичны

Запуск:
    # Локально
    uv run python scripts/demo_and_test.py

    # В Docker (если контейнеры запущены)
    docker compose exec api uv run python scripts/demo_and_test.py --verbose --no-cleanup

Аргументы:
    --no-cleanup    Не удалять тестовые данные после проверки
    --verbose       Подробный вывод
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корень проекта в path для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth import get_password_hash
from app.core.config import settings
from app.infrastructure.in_memory_queue import InMemoryTaskQueue
from app.infrastructure.redis_queue import RedisTaskQueue
from app.models import Author, Book, ReadingEvent, RecommendationCache, User
from app.recommender.service import RecommendationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo data generator and test runner")
    parser.add_argument(
        "--no-cleanup", action="store_true", help="Не удалять тестовые данные после проверки"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument(
        "--use-redis",
        action="store_true",
        help="Использовать Redis для очереди (по умолчанию: in-memory)",
    )
    return parser.parse_args()


class DemoDataGenerator:
    """Генератор демо-данных для тестирования рекомендаций."""

    USER_1 = {"username": "alice_reader", "email": "alice@demo.test"}
    USER_2 = {"username": "bob_bookworm", "email": "bob@demo.test"}

    # Авторы: словарь {name: {...}} для удобного доступа по имени
    AUTHORS = {
        "fitzgerald": {"name": "F. Scott Fitzgerald"},
        "orwell": {"name": "George Orwell"},
        "lee": {"name": "Harper Lee"},
        "austen": {"name": "Jane Austen"},
        "bronte": {"name": "Charlotte Brontë"},
        "herbert": {"name": "Frank Herbert"},
        "asimov": {"name": "Isaac Asimov"},
    }

    # Книги: теперь используем author_key вместо author_name
    SHARED_BOOKS = [
        {"title": "The Great Gatsby", "author_key": "fitzgerald", "year": 1925},
        {"title": "1984", "author_key": "orwell", "year": 1949},
        {"title": "To Kill a Mockingbird", "author_key": "lee", "year": 1960},
    ]

    ALICE_UNIQUE = [
        {"title": "Pride and Prejudice", "author_key": "austen", "year": 1813},
        {"title": "Jane Eyre", "author_key": "bronte", "year": 1847},
    ]

    BOB_UNIQUE = [
        {"title": "Dune", "author_key": "herbert", "year": 1965},
        {"title": "Foundation", "author_key": "asimov", "year": 1951},
    ]

    def __init__(self, db_session, verbose: bool = False):
        self.db = db_session
        self.verbose = verbose
        self.created_ids = {"users": [], "authors": [], "books": [], "events": []}
        # Кэш: author_key → author_id (чтобы не искать в БД повторно)
        self._author_id_cache: dict[str, int] = {}

    def _log(self, message: str):
        if self.verbose:
            logger.info(message)

    def _get_or_create_author(self, name: str) -> Author:
        author = self.db.query(Author).filter(Author.name == name).first()
        if not author:
            author = Author(name=name)
            self.db.add(author)
            self.db.flush()
            self.created_ids["authors"].append(author.id)
            self._log(f"Created author: {name} (id={author.id})")
        return author

    def _get_author_id_by_key(self, author_key: str) -> int:
        """
        Получает ID автора по ключу.

        Если автор уже в кэше — возвращает из кэша.
        Если нет — ищет в БД или создаёт нового.
        """
        # Проверяем кэш
        if author_key in self._author_id_cache:
            return self._author_id_cache[author_key]

        # Ищем в БД
        author_name = self.AUTHORS[author_key]["name"]
        author = self.db.query(Author).filter(Author.name == author_name).first()

        if not author:
            author = Author(name=author_name)
            self.db.add(author)
            self.db.flush()
            self.created_ids["authors"].append(author.id)
            self._log(f"Created author: {author_name} (id={author.id})")

        # Кэшируем и возвращаем ID
        self._author_id_cache[author_key] = author.id
        return author.id

    def _create_book(self, title: str, author_id: int, year: int) -> Book:
        """Создаёт книгу, используя author_id (как в BookCreate schema)."""
        book = Book(title=title, author_id=author_id, year=year)
        self.db.add(book)
        self.db.flush()
        self.created_ids["books"].append(book.id)
        self._log(f"Created book: '{title}' (author_id={author_id}, id={book.id})")
        return book

    def _create_user(self, username: str, email: str) -> User:
        # Проверяем, не создан ли уже
        user = self.db.query(User).filter(User.username == username).first()
        if user:
            self._log(f"User {username} already exists, skipping")
            return user

        user = User(
            username=username, email=email, hashed_password=get_password_hash("demo_password_123")
        )
        self.db.add(user)
        self.db.flush()
        self.created_ids["users"].append(user.id)
        self._log(f"Created user: {username} (id={user.id})")
        return user

    def _create_reading_event(
        self, user_id: int, book_id: int, rating: float, days_ago: int = 0
    ) -> ReadingEvent:
        event = ReadingEvent(
            user_id=user_id,
            book_id=book_id,
            rating=rating,
            completed_at=datetime.utcnow() - timedelta(days=days_ago),
        )
        self.db.add(event)
        self.db.flush()
        self.created_ids["events"].append(event.id)
        return event

    def generate(self) -> dict[str, dict]:
        logger.info("Generating demo data...")

        # === Создаём пользователей ===
        alice = self._create_user(**self.USER_1)
        bob = self._create_user(**self.USER_2)

        # === Создаём книги ===
        # Сначала предрассчитываем author_id для всех книг
        def _prep_book(book_data: dict) -> dict:
            return {
                "title": book_data["title"],
                "author_id": self._get_author_id_by_key(book_data["author_key"]),
                "year": book_data["year"],
            }

        shared = [self._create_book(**_prep_book(b)) for b in self.SHARED_BOOKS]
        alice_books = [self._create_book(**_prep_book(b)) for b in self.ALICE_UNIQUE]
        bob_books = [self._create_book(**_prep_book(b)) for b in self.BOB_UNIQUE]

        # === Создаём события чтений (без изменений) ===
        for i, book in enumerate(shared):
            self._create_reading_event(
                alice.id, book.id, rating=4.5 + (i % 2) * 0.5, days_ago=30 - i * 5
            )
        for i, book in enumerate(alice_books):
            self._create_reading_event(alice.id, book.id, rating=5.0, days_ago=20 - i * 5)

        for i, book in enumerate(shared):
            self._create_reading_event(
                bob.id, book.id, rating=4.0 + (i % 2) * 0.5, days_ago=25 - i * 5
            )
        for i, book in enumerate(bob_books):
            self._create_reading_event(bob.id, book.id, rating=5.0, days_ago=15 - i * 5)

        self.db.commit()

        logger.info("Demo data created:")
        logger.info(f"    Users: {len(self.created_ids['users'])}")
        logger.info(f"    Books: {len(self.created_ids['books'])}")
        logger.info(f"    Reading events: {len(self.created_ids['events'])}")

        return {
            "alice": alice,
            "bob": bob,
            "shared_books": shared,
            "alice_unique": alice_books,
            "bob_unique": bob_books,
        }

    def cleanup(self):
        """Удаляет созданные демо-данные (для изоляции тестов)."""
        if not self.created_ids["users"]:
            self._log("Nothing to clean up")
            return

        logger.info("Cleaning up demo data...")

        try:
            # Очищаем кэш сессии, чтобы запросы видели актуальные данные
            self.db.expire_all()

            # 1. Удаляем события чтений (зависят от users и books)
            if self.created_ids["events"]:
                self.db.execute(
                    ReadingEvent.__table__.delete().where(
                        ReadingEvent.id.in_(self.created_ids["events"])
                    )
                )
                self._log(f"Deleted {len(self.created_ids['events'])} reading events")

            # 2. Удаляем кэш рекомендаций (зависит от users)
            if self.created_ids["users"]:
                self.db.execute(
                    RecommendationCache.__table__.delete().where(
                        RecommendationCache.user_id.in_(self.created_ids["users"])
                    )
                )
                self._log("Deleted recommendation cache entries")

            # 3. Удаляем книги (зависят от authors)
            if self.created_ids["books"]:
                self.db.execute(
                    Book.__table__.delete().where(Book.id.in_(self.created_ids["books"]))
                )
                self._log(f"Deleted {len(self.created_ids['books'])} books")

            # 4. Удаляем авторов
            if self.created_ids["authors"]:
                self.db.execute(
                    Author.__table__.delete().where(Author.id.in_(self.created_ids["authors"]))
                )
                self._log(f"Deleted {len(self.created_ids['authors'])} authors")

            # 5. Удаляем пользователей (каскадно удалит связанные данные, если настроено)
            if self.created_ids["users"]:
                self.db.execute(
                    User.__table__.delete().where(User.id.in_(self.created_ids["users"]))
                )
                self._log(f"Deleted {len(self.created_ids['users'])} users")

            # Фиксируем все удаления
            self.db.commit()
            logger.info("Cleanup complete")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            self.db.rollback()
            raise


class RecommendationTester:
    """Проверка работоспособности рекомендательной системы."""

    def __init__(self, db_session, queue, verbose: bool = False):
        self.db = db_session
        self.queue = queue
        self.verbose = verbose
        self.service = RecommendationService(db=db_session)
        # Определяем тип очереди для правильной обработки
        self._is_in_memory = isinstance(queue, InMemoryTaskQueue)

    def _log(self, message: str):
        if self.verbose:
            logger.info(message)

    def trigger_recalculation(self, user_id: int) -> None:
        """Ставит задачу на пересчёт рекомендаций для пользователя."""
        self.queue.enqueue("recalculate_user", {"user_id": user_id})
        self._log(f"Enqueued recalculation task for user {user_id}")

        # Если in-memory очередь — обрабатываем задачу сразу же (синхронно)
        if self._is_in_memory:
            self._log("In-memory queue detected — processing task synchronously")
            task = self.queue.dequeue("recalculate_user", timeout=0.0)
            if task:
                from app.recommender.worker import process_recommendation_task

                process_recommendation_task(task, self.db, self.queue)
                self._log(f"Task processed synchronously for user {user_id}")

    def wait_for_processing(self, user_id: int, timeout: float = 10.0) -> bool:
        """
        Ждёт, пока рекомендации появятся в кэше.

        Для in-memory очереди возврат всегда мгновенный (обработка в trigger_recalculation).
        Для Redis — опрос с интервалом 0.5 сек.
        """
        # Для in-memory очереди не ждём — уже обработано в trigger_recalculation
        if self._is_in_memory:
            cached = self.service.get_from_cache(user_id)
            return cached is not None

        # Для Redis — опрос с разумным интервалом
        start = time.time()
        while time.time() - start < timeout:
            cached = self.service.get_from_cache(user_id)
            if cached and cached.generated_at:
                return True
            time.sleep(0.5)  # 500 мс — баланс между скоростью и нагрузкой
        return False

    def test_recommendations_logic(
        self,
        target_user_id: int,
        expected_recommended_book_ids: list[int],
        excluded_book_ids: list[int],
        description: str,
    ) -> bool:
        """
        Проверяет логику рекомендаций.

        :param target_user_id: ID пользователя, для которого проверяем
        :param expected_recommended_book_ids: книги, которые ДОЛЖНЫ быть в рекомендациях
        :param excluded_book_ids: книги, которых НЕ должно быть (уже прочитаны)
        :param description: описание проверки для лога
        :return: True если проверка прошла
        """
        logger.info(f"🔍 Testing: {description}")

        # Ждём обработки задачи
        if not self.wait_for_processing(target_user_id):
            logger.error(f"Timeout waiting for recommendations for user {target_user_id}")
            return False

        # Получаем рекомендации из кэша
        cached = self.service.get_from_cache(target_user_id)
        if not cached:
            logger.error(f"No recommendations cached for user {target_user_id}")
            return False

        recommended_ids = [r.book_id for r in cached.recommendations]
        self._log(f"   Recommended book IDs: {recommended_ids}")

        # Проверка 1: ожидаемые книги присутствуют
        missing = set(expected_recommended_book_ids) - set(recommended_ids)
        if missing:
            logger.error(f"Missing expected recommendations: {missing}")
            return False

        # Проверка 2: прочитанные книги не рекомендуются
        unwanted = set(excluded_book_ids) & set(recommended_ids)
        if unwanted:
            logger.error(f"Recommended already-read books: {unwanted}")
            return False

        logger.info(f"{description} — PASSED")
        return True

    def run_full_test(self, demo_data: dict) -> bool:
        """
        Запускает полный тест рекомендательной логики.

        Сценарий:
        - Алиса и Боб имеют схожие вкусы (3 общие книги с высокими оценками)
        - Алиса не читала уникальные книги Боба → они должны быть рекомендованы
        - Боб не читал уникальные книги Алисы → они должны быть рекомендованы
        """
        logger.info("Running recommendation tests...")

        alice = demo_data["alice"]
        bob = demo_data["bob"]
        alice_unique = demo_data["alice_unique"]
        bob_unique = demo_data["bob_unique"]

        all_passed = True

        # === Тест 1: Рекомендации для Алисы ===
        # Ожидаем: книги Боба (Dune, Foundation) в рекомендациях
        # Не ожидаем: книги, которые Алиса уже читала
        self.trigger_recalculation(alice.id)

        alice_read_ids = [book.id for book in demo_data["shared_books"] + demo_data["alice_unique"]]

        passed = self.test_recommendations_logic(
            target_user_id=alice.id,
            expected_recommended_book_ids=[book.id for book in bob_unique],
            excluded_book_ids=alice_read_ids,
            description="Alice should get Bob's unique books as recommendations",
        )
        all_passed = all_passed and passed

        # === Тест 2: Рекомендации для Боба ===
        # Ожидаем: книги Алисы (Pride and Prejudice, Jane Eyre) в рекомендациях
        self.trigger_recalculation(bob.id)

        bob_read_ids = [book.id for book in demo_data["shared_books"] + demo_data["bob_unique"]]

        passed = self.test_recommendations_logic(
            target_user_id=bob.id,
            expected_recommended_book_ids=[book.id for book in alice_unique],
            excluded_book_ids=bob_read_ids,
            description="Bob should get Alice's unique books as recommendations",
        )
        all_passed = all_passed and passed

        # === Итог ===
        if all_passed:
            logger.info("All recommendation tests PASSED!")
        else:
            logger.error("Some tests FAILED")

        return all_passed


def get_queue():
    """Создаёт очередь задач согласно настройкам."""
    if settings.USE_IN_MEMORY_QUEUE:
        return InMemoryTaskQueue()
    return RedisTaskQueue(redis_url=settings.REDIS_URL)


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(" Starting demo & test script")
    logger.info(f"   Database: {settings.DATABASE_URL}")
    logger.info(f"   Queue: {'Redis' if args.use_redis else 'In-Memory'}")

    # === Инициализация БД ===
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_pre_ping=True,
        )
        Session = sessionmaker(bind=engine)
        db = Session()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1

    # === Инициализация очереди ===
    queue = get_queue()

    try:
        # === Шаг 1: Генерация данных ===
        generator = DemoDataGenerator(db, verbose=args.verbose)
        demo_data = generator.generate()

        # === Шаг 2: Запуск тестов ===
        tester = RecommendationTester(db, queue, verbose=args.verbose)
        tests_passed = tester.run_full_test(demo_data)

        # === Шаг 3: Очистка (опционально) ===
        # === Отладка: проверка, что данные удалены ===
        if not args.no_cleanup and tests_passed:
            # Быстрая проверка: сколько осталось пользователей с демо-именами?
            remaining = (
                db.query(User)
                .filter(
                    User.username.in_(["alice_reader", "bob_bookworm"])  # ← хардкод имён
                )
                .count()
            )
            if remaining > 0:
                logger.warning(f"Warning: {remaining} demo users still in DB after cleanup")
            else:
                logger.info("Verified: demo users successfully removed")

        # === Итоговый статус ===
        if tests_passed:
            logger.info("Demo & test script completed successfully")
            return 0
        else:
            logger.error("Demo & test script completed with failures")
            return 1

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 2

    finally:
        db.close()
        if hasattr(queue, "close"):
            queue.close()


if __name__ == "__main__":
    sys.exit(main())
