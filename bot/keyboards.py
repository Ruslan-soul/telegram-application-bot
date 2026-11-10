from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Оставить заявку")]
    ],
    resize_keyboard=True
)


phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="📱 Отправить контакт",
                request_contact=True
            )
        ],
        [KeyboardButton(text="✍️ Ввести вручную")]
    ],
    resize_keyboard=True
)


service_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 Консультация")],
        [KeyboardButton(text="⚙️ Настройка")],
        [KeyboardButton(text="📦 Другая услуга")]
    ],
    resize_keyboard=True
)


comment_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пропустить")]
    ],
    resize_keyboard=True
)


confirmation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="✅ Подтвердить"),
            KeyboardButton(text="❌ Отменить")
        ]
    ],
    resize_keyboard=True
)