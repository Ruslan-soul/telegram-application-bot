
import re


ALLOWED_SERVICES = {
    "💬 Консультация",
    "⚙️ Настройка",
    "📦 Другая услуга"
}

ALLOWED_STATUSES = {
    "new",
    "in_progress",
    "completed",
    "cancelled"
}

USERNAME_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]{4,31}$"
)

PHONE_PATTERN = re.compile(
    r"^\+?[0-9() -]+$"
)


def validate_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Имя должно быть текстом.")

    name = value.strip()

    if not name:
        raise ValueError("Имя не может быть пустым.")

    if len(name) > 60:
        raise ValueError("Имя не должно превышать 60 символов.")

    if not any(char.isalpha() for char in name):
        raise ValueError("Имя должно содержать буквы.")

    allowed_punctuation = " -'’."

    if any(
        not (
            char.isalpha()
            or char.isspace()
            or char in allowed_punctuation
        )
        for char in name
    ):
        raise ValueError("Имя содержит недопустимые символы.")

    return name


def validate_phone(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Телефон должен быть текстом.")

    phone = value.strip()

    if not phone:
        raise ValueError("Телефон не может быть пустым.")

    if not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Телефон содержит недопустимые символы.")

    digits = re.sub(r"\D", "", phone)

    if not 10 <= len(digits) <= 15:
        raise ValueError(
            "Номер должен содержать от 10 до 15 цифр."
        )

    return phone


def validate_service(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Услуга должна быть текстом.")

    if value not in ALLOWED_SERVICES:
        raise ValueError("Выбрана неизвестная услуга.")

    return value


def validate_comment(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Комментарий должен быть текстом.")

    comment = value.strip()

    if not comment:
        comment = "Не указан"

    if len(comment) > 1000:
        raise ValueError(
            "Комментарий не должен превышать 1000 символов."
        )

    return comment


def validate_username(value: str | None) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("Некорректный username.")

    username = value.strip()

    if not username:
        return None

    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username должен содержать от 5 до 32 символов: "
            "латинские буквы, цифры и нижнее подчёркивание. "
            "Первый символ должен быть буквой."
        )

    return username


def validate_application_data(
    user_id: int,
    username: str | None,
    name: str,
    phone: str,
    service: str,
    comment: str
) -> dict:

    if (
        not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
    ):
        raise ValueError("Некорректный ID пользователя.")

    return {
        "user_id": user_id,
        "username": validate_username(username),
        "name": validate_name(name),
        "phone": validate_phone(phone),
        "service": validate_service(service),
        "comment": validate_comment(comment)
    }
