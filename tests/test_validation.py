
import pytest

from bot.validation import (
    validate_name,
    validate_phone,
    validate_service,
    validate_comment,
    validate_username,
    validate_application_data
)


# =========================
# Проверка имени
# =========================

def test_valid_name():
    assert validate_name(" Руслан ") == "Руслан"


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        "123456",
        "Руслан@",
        "А" * 61,
        None,
        123,
        True
    ]
)
def test_invalid_name(name):
    with pytest.raises(ValueError):
        validate_name(name)


def test_name_with_hyphen():
    assert validate_name("Анна-Мария") == "Анна-Мария"


def test_name_with_apostrophe():
    assert validate_name("O'Connor") == "O'Connor"


# =========================
# Проверка телефона
# =========================

@pytest.mark.parametrize(
    "phone",
    [
        "+79991234567",
        "8 (999) 123-45-67",
        "79991234567",
        "+1 202 555 0123"
    ]
)
def test_valid_phone(phone):
    assert validate_phone(phone) == phone


@pytest.mark.parametrize(
    "phone",
    [
        "",
        "   ",
        "12345",
        "абвгдежзий",
        "+7999abc12345",
        "++79991234567",
        "7999+1234567",
        "++++++++79991234567",
        "1234567890123456",
        None,
        79991234567,
        True
    ]
)
def test_invalid_phone(phone):
    with pytest.raises(ValueError):
        validate_phone(phone)


# =========================
# Проверка услуги
# =========================

def test_valid_service():
    assert (
        validate_service("💬 Консультация")
        == "💬 Консультация"
    )


@pytest.mark.parametrize(
    "service",
    [
        "Взлом NASA",
        "",
        None,
        123,
        True
    ]
)
def test_invalid_service(service):
    with pytest.raises(ValueError):
        validate_service(service)


# =========================
# Проверка комментария
# =========================

def test_empty_comment():
    assert validate_comment("   ") == "Не указан"


def test_valid_comment():
    assert (
        validate_comment(" Помогите настроить ")
        == "Помогите настроить"
    )


def test_too_long_comment():
    with pytest.raises(ValueError):
        validate_comment("А" * 1001)


def test_comment_at_limit():
    comment = "А" * 1000

    assert validate_comment(comment) == comment


def test_invalid_comment_type():
    with pytest.raises(ValueError):
        validate_comment(123)


# =========================
# Проверка username
# =========================

@pytest.mark.parametrize(
    "username",
    [
        "test_user",
        "Ruslan123",
        "user_12345"
    ]
)
def test_valid_username(username):
    assert validate_username(username) == username


@pytest.mark.parametrize(
    "username",
    [
        "abcd",
        "ab cd",
        "test-user",
        "@test_user",
        "тестовый",
        "1test_user",
        "a" * 33,
        123,
        True
    ]
)
def test_invalid_username(username):
    with pytest.raises(ValueError):
        validate_username(username)


def test_empty_username():
    assert validate_username("") is None


def test_username_with_spaces():
    assert validate_username(" test_user ") == "test_user"


def test_none_username():
    assert validate_username(None) is None


# =========================
# Проверка всей заявки
# =========================

def test_valid_application_data():
    data = validate_application_data(
        user_id=123456,
        username="test_user",
        name="Руслан",
        phone="+79991234567",
        service="💬 Консультация",
        comment="Помогите настроить"
    )

    assert data["name"] == "Руслан"
    assert data["phone"] == "+79991234567"
    assert data["user_id"] == 123456
    assert data["username"] == "test_user"


def test_application_with_empty_username():
    data = validate_application_data(
        user_id=123456,
        username="",
        name="Руслан",
        phone="+79991234567",
        service="💬 Консультация",
        comment="Тест"
    )

    assert data["username"] is None


@pytest.mark.parametrize(
    "user_id",
    [
        0,
        -1,
        True,
        False,
        "123456",
        None
    ]
)
def test_invalid_user_id(user_id):
    with pytest.raises(ValueError):
        validate_application_data(
            user_id=user_id,
            username="test_user",
            name="Руслан",
            phone="+79991234567",
            service="💬 Консультация",
            comment="Тест"
        )


def test_invalid_application_data():
    with pytest.raises(ValueError):
        validate_application_data(
            user_id=123456,
            username="test_user",
            name="12345",
            phone="+79991234567",
            service="💬 Консультация",
            comment="Тест"
        )


def test_invalid_username_in_application():
    with pytest.raises(ValueError):
        validate_application_data(
            user_id=123456,
            username="bad username",
            name="Руслан",
            phone="+79991234567",
            service="💬 Консультация",
            comment="Тест"
        )
