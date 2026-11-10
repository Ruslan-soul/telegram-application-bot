import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.states import ApplicationForm

from bot.keyboards import (
    main_keyboard,
    phone_keyboard,
    service_keyboard,
    comment_keyboard,
    confirmation_keyboard
)

from bot.database.repository import create_application

from bot.validation import (
    validate_name,
    validate_phone,
    validate_service,
    validate_comment,
    validate_application_data
)

from bot.notifications import notify_admins


router = Router()


# Отмена оформления заявки
@router.message(Command("cancel"))
async def cancel_application(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "Заявка отменена. Если захочешь начать заново — нажми кнопку.",
        reply_markup=main_keyboard
    )


# Начало оформления
@router.message(F.text == "📝 Оставить заявку")
async def create_application_handler(
    message: Message,
    state: FSMContext
):
    await state.clear()
    await state.set_state(ApplicationForm.name)

    await message.answer(
        "Давай оформим заявку! 🚀\n\n"
        "Для начала напиши своё имя.",
        reply_markup=ReplyKeyboardRemove()
    )


# Получение имени
@router.message(ApplicationForm.name)
async def get_name(
    message: Message,
    state: FSMContext
):
    try:
        name = validate_name(message.text)

    except ValueError as error:
        await message.answer(
            f"{error}\nПопробуй ещё раз."
        )
        return

    await state.update_data(name=name)
    await state.set_state(ApplicationForm.phone)

    await message.answer(
        f"Приятно познакомиться, {name}! 😎\n\n"
        "Как передашь номер телефона?",
        reply_markup=phone_keyboard
    )


# Ручной ввод телефона
@router.message(
    ApplicationForm.phone,
    F.text == "✍️ Ввести вручную"
)
async def manual_phone(message: Message):
    await message.answer(
        "Напиши номер телефона.\n"
        "Например: +79991234567",
        reply_markup=ReplyKeyboardRemove()
    )


# Получение контакта Telegram
@router.message(ApplicationForm.phone, F.contact)
async def get_contact(
    message: Message,
    state: FSMContext
):
    contact = message.contact

    if (
        contact.user_id is not None
        and contact.user_id != message.from_user.id
    ):
        await message.answer(
            "Пожалуйста, отправь именно свой контакт."
        )
        return

    try:
        phone = validate_phone(contact.phone_number)

    except ValueError as error:
        await message.answer(
            f"{error}\nПопробуй отправить номер вручную."
        )
        return

    await process_phone(message, state, phone)


# Ручное получение телефона
@router.message(ApplicationForm.phone)
async def get_phone(
    message: Message,
    state: FSMContext
):
    try:
        phone = validate_phone(message.text)

    except ValueError as error:
        await message.answer(
            f"{error}\n"
            "Пример правильного формата: +79991234567"
        )
        return

    await process_phone(message, state, phone)


# Общая обработка телефона
async def process_phone(
    message: Message,
    state: FSMContext,
    phone: str
):
    await state.update_data(phone=phone)
    await state.set_state(ApplicationForm.service)

    await message.answer(
        "Отлично! 📱\n\n"
        "Какую услугу ты хочешь заказать?",
        reply_markup=service_keyboard
    )


# Выбор услуги
@router.message(ApplicationForm.service)
async def get_service(
    message: Message,
    state: FSMContext
):
    try:
        service = validate_service(message.text)

    except ValueError:
        await message.answer(
            "Выбери услугу с помощью кнопок ниже.",
            reply_markup=service_keyboard
        )
        return

    await state.update_data(service=service)
    await state.set_state(ApplicationForm.comment)

    await message.answer(
        "Есть дополнительные пожелания или комментарии?\n\n"
        "Напиши их сообщением или нажми «Пропустить».",
        reply_markup=comment_keyboard
    )


# Получение комментария
@router.message(ApplicationForm.comment)
async def get_comment(
    message: Message,
    state: FSMContext
):
    if message.text is None:
        await message.answer(
            "Напиши комментарий текстом или пропусти."
        )
        return

    raw_comment = message.text.strip()

    if raw_comment == "Пропустить":
        raw_comment = ""

    try:
        comment = validate_comment(raw_comment)

    except ValueError as error:
        await message.answer(str(error))
        return

    await state.update_data(comment=comment)
    await state.set_state(ApplicationForm.confirmation)

    data = await state.get_data()

    await message.answer(
        "Проверь свою заявку:\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🛠 Услуга: {data['service']}\n"
        f"💬 Комментарий: {data['comment']}\n\n"
        "Всё верно?",
        reply_markup=confirmation_keyboard
    )


# Подтверждение заявки и сохранение в БД
@router.message(
    ApplicationForm.confirmation,
    F.text == "✅ Подтвердить"
)
async def confirm_application(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    data = await state.get_data()

    # Проверяем целостность данных
    try:
        data = validate_application_data(
            user_id=message.from_user.id,
            username=message.from_user.username,
            name=data["name"],
            phone=data["phone"],
            service=data["service"],
            comment=data["comment"]
        )

    except (ValueError, KeyError, TypeError):
        logging.exception(
            "Некорректные или неполные данные заявки от пользователя %s",
            message.from_user.id
        )

        await state.clear()

        await message.answer(
            "Не удалось проверить данные заявки.\n"
            "Пожалуйста, начни оформление заново.",
            reply_markup=main_keyboard
        )
        return

    # Сохраняем заявку
    try:
        application_id = await create_application(
            user_id=data["user_id"],
            username=data["username"],
            name=data["name"],
            phone=data["phone"],
            service=data["service"],
            comment=data["comment"]
        )

    except Exception:
        logging.exception(
            "Не удалось сохранить заявку в БД. Пользователь: %s",
            message.from_user.id
        )

        await message.answer(
            "Не удалось сохранить заявку из-за технической ошибки.\n"
            "Твои данные пока не потеряны. "
            "Попробуй подтвердить ещё раз."
        )
        return

    # Заявка сохранена — закрываем FSM,
    # чтобы повторное подтверждение не создало дубликат
    await state.clear()

    # Уведомляем администраторов
    try:
        await notify_admins(
            bot=bot,
            application_id=application_id,
            data=data
        )

    except Exception:
        logging.exception(
            "Ошибка при отправке уведомлений администраторам "
            "для заявки №%s",
            application_id
        )

    # Подтверждаем оформление клиенту
    await message.answer(
        "Заявка успешно оформлена! 🎉\n\n"
        f"Спасибо, {data['name']}!\n"
        f"Номер заявки: №{application_id}\n\n"
        "Мы получили твои данные и скоро свяжемся с тобой.",
        reply_markup=main_keyboard
    )


# Отмена на этапе подтверждения
@router.message(
    ApplicationForm.confirmation,
    F.text == "❌ Отменить"
)
async def reject_application(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "Заявка отменена. Можешь оформить новую в любое время.",
        reply_markup=main_keyboard
    )


# Защита от непонятных сообщений при подтверждении
@router.message(ApplicationForm.confirmation)
async def unknown_confirmation(message: Message):
    await message.answer(
        "Пожалуйста, выбери «Подтвердить» или «Отменить»."
    )