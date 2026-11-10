
import aiosqlite

from bot.config import DB_PATH
from bot.validation import (
    validate_application_data,
    ALLOWED_STATUSES
)


def validate_id(value: int):
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
    ):
        raise ValueError("ID должен быть положительным числом.")


def validate_limit(limit: int):
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= 100
    ):
        raise ValueError("Лимит должен быть от 1 до 100.")


def validate_offset(offset: int):
    if (
        not isinstance(offset, int)
        or isinstance(offset, bool)
        or offset < 0
    ):
        raise ValueError("Некорректное смещение.")


def validate_status(status: str):
    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        raise ValueError("Недопустимый статус.")


def validate_optional_status(status: str | None):
    if status is not None:
        validate_status(status)


# Создание новой заявки
async def create_application(
    user_id: int,
    username: str | None,
    name: str,
    phone: str,
    service: str,
    comment: str
) -> int:

    data = validate_application_data(
        user_id=user_id,
        username=username,
        name=name,
        phone=phone,
        service=service,
        comment=comment
    )

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO applications (
                user_id, username, name,
                phone, service, comment
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["user_id"],
                data["username"],
                data["name"],
                data["phone"],
                data["service"],
                data["comment"]
            )
        )

        await db.commit()

        return cursor.lastrowid


# Получение списка заявок с фильтром и пагинацией
async def get_applications(
    limit: int = 10,
    status: str | None = None,
    offset: int = 0
):
    validate_limit(limit)
    validate_offset(offset)
    validate_optional_status(status)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if status is not None:
            cursor = await db.execute(
                """
                SELECT id, name, phone, service, status, created_at
                FROM applications
                WHERE status = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (status, limit, offset)
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, name, phone, service, status, created_at
                FROM applications
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )

        rows = await cursor.fetchall()

        return [dict(row) for row in rows]


# Количество заявок для пагинации
async def get_applications_count(
    status: str | None = None
):
    validate_optional_status(status)

    async with aiosqlite.connect(DB_PATH) as db:
        if status is not None:
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM applications
                WHERE status = ?
                """,
                (status,)
            )
        else:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM applications"
            )

        result = await cursor.fetchone()

        return result[0]


# Получение одной заявки
async def get_application(application_id: int):
    validate_id(application_id)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM applications
            WHERE id = ?
            """,
            (application_id,)
        )

        row = await cursor.fetchone()

        return dict(row) if row else None


# Изменение статуса
async def update_application_status(
    application_id: int,
    status: str
):
    validate_id(application_id)
    validate_status(status)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE applications
            SET status = ?
            WHERE id = ?
            """,
            (status, application_id)
        )

        await db.commit()

        return cursor.rowcount > 0


# Поиск заявок по ID, имени или телефону
async def search_applications(
    query: str,
    limit: int = 10
):
    validate_limit(limit)

    if not isinstance(query, str):
        raise ValueError("Поисковый запрос должен быть текстом.")

    query = query.strip()

    if not query or len(query) > 100:
        raise ValueError(
            "Запрос должен содержать от 1 до 100 символов."
        )

    # Экранируем специальные символы LIKE.
    # Они будут искаться как обычный текст.
    escaped_query = (
        query
        .replace("!", "!!")
        .replace("%", "!%")
        .replace("_", "!_")
    )

    search_value = f"%{escaped_query}%"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT id, name, phone, service, status, created_at
            FROM applications
            WHERE
                CAST(id AS TEXT) LIKE ? ESCAPE '!'
                OR name LIKE ? ESCAPE '!'
                OR phone LIKE ? ESCAPE '!'
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                search_value,
                search_value,
                search_value,
                limit
            )
        )

        rows = await cursor.fetchall()

        return [dict(row) for row in rows]


# Статистика заявок
async def get_application_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT status, COUNT(*)
            FROM applications
            GROUP BY status
            """
        )

        rows = await cursor.fetchall()

        stats = {
            "new": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0
        }

        for status, count in rows:
            if status in stats:
                stats[status] = count

        stats["total"] = sum(count for _, count in rows)

        return stats


# Получение всех заявок для экспорта
async def get_all_applications():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                username,
                name,
                phone,
                service,
                comment,
                status,
                created_at
            FROM applications
            ORDER BY id DESC
            """
        )

        rows = await cursor.fetchall()

        return [dict(row) for row in rows]
