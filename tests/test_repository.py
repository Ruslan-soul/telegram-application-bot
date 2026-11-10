
import asyncio

import pytest

from bot.database import db as database
from bot.database import repository


@pytest.fixture
def run_db(tmp_path, monkeypatch):
    """
    Для каждого теста создаётся отдельная временная база.
    Рабочая applications.db не затрагивается.
    """
    db_path = str(tmp_path / "test_applications.db")

    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(repository, "DB_PATH", db_path)

    asyncio.run(database.init_db())

    return asyncio.run


def create_test_application(run_db, **overrides):
    data = {
        "user_id": 123456,
        "username": "test_user",
        "name": "Руслан",
        "phone": "+79991234567",
        "service": "💬 Консультация",
        "comment": "Тестовая заявка"
    }
    data.update(overrides)

    return run_db(repository.create_application(**data))


# Создание и получение заявки
def test_create_and_get_application(run_db):
    application_id = create_test_application(run_db)

    application = run_db(
        repository.get_application(application_id)
    )

    assert application is not None
    assert application["name"] == "Руслан"
    assert application["phone"] == "+79991234567"
    assert application["status"] == "new"


# Получение несуществующей заявки
def test_get_missing_application(run_db):
    assert run_db(repository.get_application(999)) is None


# Изменение статуса
def test_update_application_status(run_db):
    application_id = create_test_application(run_db)

    result = run_db(
        repository.update_application_status(
            application_id,
            "completed"
        )
    )

    application = run_db(
        repository.get_application(application_id)
    )

    assert result is True
    assert application["status"] == "completed"


def test_update_missing_application(run_db):
    result = run_db(
        repository.update_application_status(999, "completed")
    )

    assert result is False


# Проверка списка и пагинации
def test_get_applications_and_pagination(run_db):
    create_test_application(run_db, name="Первый")
    create_test_application(run_db, name="Второй")
    create_test_application(run_db, name="Третий")

    applications = run_db(
        repository.get_applications(limit=2)
    )

    assert len(applications) == 2
    assert applications[0]["name"] == "Третий"
    assert applications[1]["name"] == "Второй"

    next_page = run_db(
        repository.get_applications(limit=2, offset=2)
    )

    assert len(next_page) == 1
    assert next_page[0]["name"] == "Первый"


# Фильтрация по статусу
def test_get_applications_by_status(run_db):
    first_id = create_test_application(run_db)
    create_test_application(run_db, name="Вторая")

    run_db(
        repository.update_application_status(
            first_id,
            "completed"
        )
    )

    applications = run_db(
        repository.get_applications(status="completed")
    )

    assert len(applications) == 1
    assert applications[0]["id"] == first_id


# Подсчёт заявок
def test_get_applications_count(run_db):
    first_id = create_test_application(run_db)
    create_test_application(run_db, name="Вторая")

    run_db(
        repository.update_application_status(
            first_id,
            "completed"
        )
    )

    assert run_db(repository.get_applications_count()) == 2

    assert run_db(
        repository.get_applications_count("completed")
    ) == 1

    assert run_db(
        repository.get_applications_count("new")
    ) == 1


# Поиск
def test_search_applications(run_db):
    create_test_application(
        run_db,
        name="Александр",
        phone="+79991112233"
    )

    by_name = run_db(
        repository.search_applications("Александр")
    )

    by_phone = run_db(
        repository.search_applications("1112233")
    )

    by_id = run_db(
        repository.search_applications("1")
    )

    assert len(by_name) == 1
    assert len(by_phone) == 1
    assert len(by_id) == 1


# Статистика
def test_get_application_stats(run_db):
    first_id = create_test_application(run_db)
    create_test_application(run_db, name="Вторая")
    create_test_application(run_db, name="Третья")

    run_db(
        repository.update_application_status(
            first_id,
            "completed"
        )
    )

    stats = run_db(repository.get_application_stats())

    assert stats == {
        "new": 2,
        "in_progress": 0,
        "completed": 1,
        "cancelled": 0,
        "total": 3
    }


# Получение всех заявок для Excel
def test_get_all_applications(run_db):
    create_test_application(run_db)
    create_test_application(run_db, name="Вторая")

    applications = run_db(
        repository.get_all_applications()
    )

    assert len(applications) == 2
    assert applications[0]["name"] == "Вторая"
    assert "username" in applications[0]
    assert "comment" in applications[0]


# Проверка некорректных ID
@pytest.mark.parametrize("application_id", [0, -1, True, "123"])
def test_invalid_application_id(run_db, application_id):
    with pytest.raises(ValueError):
        run_db(repository.get_application(application_id))


# Проверка некорректных лимитов
@pytest.mark.parametrize("limit", [0, -1, 101, True, "10"])
def test_invalid_limit(run_db, limit):
    with pytest.raises(ValueError):
        run_db(repository.get_applications(limit=limit))


# Проверка некорректного смещения
@pytest.mark.parametrize("offset", [-1, True, "10"])
def test_invalid_offset(run_db, offset):
    with pytest.raises(ValueError):
        run_db(repository.get_applications(offset=offset))


# Проверка некорректных поисковых запросов
@pytest.mark.parametrize("query", ["", "   ", "А" * 101, 123])
def test_invalid_search_query(run_db, query):
    with pytest.raises(ValueError):
        run_db(repository.search_applications(query))


# Проверка недопустимого статуса
def test_invalid_status(run_db):
    with pytest.raises(ValueError):
        run_db(
            repository.update_application_status(1, "unknown")
        )

# Проверка статуса при изменении заявки
@pytest.mark.parametrize("status", [123, [], None, True])
def test_invalid_status_types_on_update(run_db, status):
    with pytest.raises(ValueError):
        run_db(
            repository.update_application_status(1, status)
        )


# Проверка статуса при получении списка заявок
@pytest.mark.parametrize("status", [123, [], True])
def test_invalid_status_types_on_get(run_db, status):
    with pytest.raises(ValueError):
        run_db(
            repository.get_applications(status=status)
        )


# Проверка статуса при подсчёте заявок
@pytest.mark.parametrize("status", [123, [], True])
def test_invalid_status_types_on_count(run_db, status):
    with pytest.raises(ValueError):
        run_db(
            repository.get_applications_count(status=status)
        )


# Проверка специальных символов SQL LIKE
@pytest.mark.parametrize("query", ["%", "_"])
def test_search_special_like_symbols(run_db, query):
    create_test_application(run_db)

    results = run_db(
        repository.search_applications(query)
    )

    assert results == []
