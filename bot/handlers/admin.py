import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import ADMIN_IDS
from bot.database.backup import create_backup
from bot.database.repository import (
    get_all_applications,
    get_application,
    get_application_stats,
    get_applications,
    get_applications_count,
    search_applications,
    update_application_status,
)
from bot.excel_export import create_excel_report
from bot.validation import ALLOWED_STATUSES


router = Router()

PAGE_SIZE = 10

STATUS_NAMES = {
    "new": "🆕 Новая",
    "in_progress": "🔄 В работе",
    "completed": "✅ Завершена",
    "cancelled": "❌ Отменена",
}

FILTER_NAMES = {
    "all": "Все",
    "new": "Новые",
    "in_progress": "В работе",
    "completed": "Завершённые",
    "cancelled": "Отменённые",
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def parse_positive_id(value: str) -> int:
    """Преобразует строку в положительный ID заявки."""
    if not value.isdigit():
        raise ValueError("Некорректный ID заявки.")

    application_id = int(value)

    if application_id <= 0:
        raise ValueError("ID заявки должен быть положительным.")

    return application_id


def parse_page(value: str) -> int:
    """Преобразует строку в неотрицательный номер страницы."""
    if not value.isdigit():
        raise ValueError("Некорректный номер страницы.")

    return int(value)


def applications_keyboard(
    applications,
    status="all",
    page=0,
    total_pages=1,
):
    buttons = []

    for application in applications:
        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"№{application['id']} — "
                    f"{application['name']} | "
                    f"{STATUS_NAMES.get(application['status'], application['status'])}"
                ),
                callback_data=f"admin:view:{application['id']}",
            )
        ])

    buttons.extend([
        [
            InlineKeyboardButton(
                text="📋 Все",
                callback_data="admin:page:all:0",
            ),
            InlineKeyboardButton(
                text="🆕 Новые",
                callback_data="admin:page:new:0",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 В работе",
                callback_data="admin:page:in_progress:0",
            ),
            InlineKeyboardButton(
                text="✅ Завершённые",
                callback_data="admin:page:completed:0",
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменённые",
                callback_data="admin:page:cancelled:0",
            )
        ],
    ])

    if total_pages > 1:
        navigation = []

        if page > 0:
            navigation.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"admin:page:{status}:{page - 1}",
                )
            )

        if page < total_pages - 1:
            navigation.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️",
                    callback_data=f"admin:page:{status}:{page + 1}",
                )
            )

        if navigation:
            buttons.append(navigation)

    buttons.extend([
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="admin:stats",
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"admin:page:{status}:{page}",
            )
        ],
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def show_applications(
    message: Message,
    status="all",
    page=0,
):
    if status not in FILTER_NAMES:
        status = "all"

    try:
        db_status = None if status == "all" else status

        total = await get_applications_count(db_status)

        total_pages = max(
            1,
            (total + PAGE_SIZE - 1) // PAGE_SIZE
        )

        page = max(0, min(page, total_pages - 1))

        applications = await get_applications(
            limit=PAGE_SIZE,
            status=db_status,
            offset=page * PAGE_SIZE,
        )

    except Exception:
        logging.exception("Не удалось загрузить список заявок")

        await message.answer(
            "Не удалось загрузить заявки из базы данных. "
            "Попробуй позже."
        )
        return

    if not applications:
        text = (
            f"📋 Заявки: {FILTER_NAMES[status]}\n\n"
            "Заявок пока нет."
        )
    else:
        text = (
            f"📋 Заявки: {FILTER_NAMES[status]}\n"
            f"Найдено: {total}\n"
            f"Страница: {page + 1}/{total_pages}\n\n"
            "Выбери заявку:"
        )

    await message.answer(
        text,
        reply_markup=applications_keyboard(
            applications,
            status,
            page,
            total_pages,
        ),
    )


async def show_application(
    callback: CallbackQuery,
    application_id: int
) -> bool:
    """Показывает карточку заявки. Возвращает False при ошибке."""

    try:
        application = await get_application(application_id)

    except Exception:
        logging.exception(
            "Не удалось получить заявку №%s",
            application_id,
        )
        return False

    if not application:
        return False

    status = STATUS_NAMES.get(
        application["status"],
        application["status"],
    )

    text = (
        f"📄 Заявка №{application['id']}\n\n"
        f"👤 Имя: {application['name']}\n"
        f"📱 Телефон: {application['phone']}\n"
        f"🛠 Услуга: {application['service']}\n"
        f"💬 Комментарий: {application['comment'] or 'Не указан'}\n"
        f"📌 Статус: {status}\n"
        f"🕒 Создана: {application['created_at']}\n"
        f"🆔 Telegram ID: {application['user_id']}\n"
        f"👨‍💻 Username: @{application['username'] or 'не указан'}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 Новая",
                    callback_data=f"admin:status:{application_id}:new",
                ),
                InlineKeyboardButton(
                    text="🔄 В работе",
                    callback_data=f"admin:status:{application_id}:in_progress",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершена",
                    callback_data=f"admin:status:{application_id}:completed",
                ),
                InlineKeyboardButton(
                    text="❌ Отменена",
                    callback_data=f"admin:status:{application_id}:cancelled",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К списку",
                    callback_data="admin:page:all:0",
                )
            ],
        ]
    )

    if (
        callback.message is None
        or not hasattr(callback.message, "edit_text")
    ):
        return False

    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
        )
        return True

    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return True

        logging.exception(
            "Telegram не смог обновить карточку заявки №%s",
            application_id,
        )
        return False

    except TelegramAPIError:
        logging.exception(
            "Ошибка Telegram при обновлении карточки заявки №%s",
            application_id,
        )
        return False@router.message(Command("myid"))
async def show_my_id(message: Message):
    await message.answer(
        f"Твой Telegram ID: {message.from_user.id}"
    )


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет доступа.")
        return

    await show_applications(message)


@router.message(Command("find"))
async def find_applications(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет доступа.")
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Напиши поисковый запрос после команды.\n\n"
            "Например:\n"
            "/find Алексей\n"
            "/find 590601137\n"
            "/find 79991234567"
        )
        return

    query = parts[1].strip()

    try:
        applications = await search_applications(query)

    except ValueError as error:
        await message.answer(str(error))
        return

    except Exception:
        logging.exception("Ошибка поиска заявок")

        await message.answer(
            "Не удалось выполнить поиск. Попробуй позже."
        )
        return

    if not applications:
        await message.answer(
            "По твоему запросу ничего не найдено."
        )
        return

    buttons = []

    for application in applications:
        buttons.append([
            InlineKeyboardButton(
                text=f"№{application['id']} — {application['name']}",
                callback_data=f"admin:view:{application['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ К админке",
            callback_data="admin:page:all:0",
        )
    ])

    await message.answer(
        f"🔎 Результаты поиска: {len(applications)}\n\n"
        "Выбери заявку:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
    )


@router.callback_query(F.data.startswith("admin:page:"))
async def change_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        parts = callback.data.split(":")

        if len(parts) != 4:
            raise ValueError("Некорректный формат пагинации.")

        status = parts[2]

        if status not in FILTER_NAMES:
            raise ValueError("Неизвестный фильтр.")

        page = parse_page(parts[3])

        db_status = None if status == "all" else status

        total = await get_applications_count(db_status)

        total_pages = max(
            1,
            (total + PAGE_SIZE - 1) // PAGE_SIZE
        )

        page = min(page, total_pages - 1)

        applications = await get_applications(
            limit=PAGE_SIZE,
            status=db_status,
            offset=page * PAGE_SIZE,
        )

    except ValueError:
        await callback.answer(
            "Некорректные данные кнопки.",
            show_alert=True
        )
        return

    except Exception:
        logging.exception(
            "Не удалось загрузить страницу заявок"
        )

        await callback.answer(
            "Не удалось загрузить заявки. Попробуй позже.",
            show_alert=True,
        )
        return

    if not applications:
        text = (
            f"📋 Заявки: {FILTER_NAMES[status]}\n\n"
            "Заявок пока нет."
        )
    else:
        text = (
            f"📋 Заявки: {FILTER_NAMES[status]}\n"
            f"Найдено: {total}\n"
            f"Страница: {page + 1}/{total_pages}\n\n"
            "Выбери заявку:"
        )

    if (
        callback.message is None
        or not hasattr(callback.message, "edit_text")
    ):
        await callback.answer(
            "Не удалось обновить сообщение.",
            show_alert=True
        )
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=applications_keyboard(
                applications,
                status,
                page,
                total_pages,
            ),
        )

    except TelegramBadRequest as error:
        if "message is not modified" not in str(error).lower():
            logging.exception(
                "Не удалось обновить страницу админки"
            )

            await callback.answer(
                "Не удалось обновить список.",
                show_alert=True
            )
            return

    except TelegramAPIError:
        logging.exception(
            "Ошибка Telegram при обновлении списка заявок"
        )

        await callback.answer(
            "Ошибка Telegram. Попробуй ещё раз.",
            show_alert=True
        )
        return

    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def show_statistics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        stats = await get_application_stats()

    except Exception:
        logging.exception(
            "Не удалось получить статистику заявок"
        )

        await callback.answer(
            "Не удалось загрузить статистику.",
            show_alert=True
        )
        return

    text = (
        "📊 СТАТИСТИКА ЗАЯВОК\n\n"
        f"📦 Всего заявок: {stats['total']}\n\n"
        f"🆕 Новые: {stats['new']}\n"
        f"🔄 В работе: {stats['in_progress']}\n"
        f"✅ Завершённые: {stats['completed']}\n"
        f"❌ Отменённые: {stats['cancelled']}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К заявкам",
                    callback_data="admin:page:all:0",
                )
            ]
        ]
    )

    if (
        callback.message is None
        or not hasattr(callback.message, "edit_text")
    ):
        await callback.answer(
            "Не удалось обновить сообщение.",
            show_alert=True
        )
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )

    except TelegramBadRequest as error:
        if "message is not modified" not in str(error).lower():
            logging.exception(
                "Не удалось показать статистику"
            )

            await callback.answer(
                "Не удалось обновить статистику.",
                show_alert=True
            )
            return

    except TelegramAPIError:
        logging.exception(
            "Ошибка Telegram при показе статистики"
        )

        await callback.answer(
            "Ошибка Telegram. Попробуй ещё раз.",
            show_alert=True
        )
        return

    await callback.answer()


@router.callback_query(F.data.startswith("admin:view:"))
async def open_application(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        parts = callback.data.split(":")

        if len(parts) != 3:
            raise ValueError

        application_id = parse_positive_id(parts[2])

    except ValueError:
        await callback.answer(
            "Некорректный ID заявки.",
            show_alert=True
        )
        return

    try:
        application = await get_application(application_id)

    except Exception:
        logging.exception(
            "Ошибка получения заявки №%s",
            application_id
        )

        await callback.answer(
            "Не удалось загрузить заявку.",
            show_alert=True
        )
        return

    if not application:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    if not await show_application(callback, application_id):
        await callback.answer(
            "Не удалось открыть карточку заявки.",
            show_alert=True
        )
        return

    await callback.answer()@router.callback_query(F.data.startswith("admin:status:"))
async def change_status(
    callback: CallbackQuery,
    bot: Bot
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        parts = callback.data.split(":")

        if len(parts) != 4:
            raise ValueError

        application_id = parse_positive_id(parts[2])
        status = parts[3]

        if status not in ALLOWED_STATUSES:
            raise ValueError

    except ValueError:
        await callback.answer(
            "Некорректные данные изменения статуса.",
            show_alert=True
        )
        return

    try:
        old_application = await get_application(application_id)

        if not old_application:
            await callback.answer(
                "Заявка не найдена.",
                show_alert=True
            )
            return

        if old_application["status"] == status:
            await callback.answer(
                "Этот статус уже установлен."
            )
            return

        updated = await update_application_status(
            application_id,
            status
        )

        if not updated:
            await callback.answer(
                "Не удалось изменить статус.",
                show_alert=True
            )
            return

        application = await get_application(application_id)

    except Exception:
        logging.exception(
            "Ошибка изменения статуса заявки №%s",
            application_id
        )

        await callback.answer(
            "Не удалось изменить статус из-за ошибки базы данных.",
            show_alert=True
        )
        return

    if not application:
        await callback.answer(
            "Статус сохранён, но заявку не удалось повторно загрузить.",
            show_alert=True
        )
        return

    status_name = STATUS_NAMES[status]

    # Уведомляем клиента
    try:
        await bot.send_message(
            chat_id=application["user_id"],
            text=(
                f"Здравствуйте, {application['name']}!\n\n"
                f"Статус вашей заявки №{application_id} изменён.\n\n"
                f"📌 Новый статус: {status_name}"
            ),
        )

        notification_sent = True

    except TelegramAPIError:
        logging.exception(
            "Не удалось уведомить клиента по заявке №%s",
            application_id
        )
        notification_sent = False

    except Exception:
        logging.exception(
            "Неожиданная ошибка уведомления клиента по заявке №%s",
            application_id
        )
        notification_sent = False

    # Обновляем карточку администратора
    card_updated = await show_application(
        callback,
        application_id
    )

    if not card_updated:
        if notification_sent:
            await callback.answer(
                "Статус изменён, клиент уведомлён. "
                "Карточку обновить не удалось.",
                show_alert=True
            )
        else:
            await callback.answer(
                "Статус сохранён, но уведомление "
                "и обновление карточки не удались.",
                show_alert=True
            )
        return

    if notification_sent:
        await callback.answer(
            "Статус изменён, клиент уведомлён!"
        )
    else:
        await callback.answer(
            "Статус сохранён, но уведомление не доставлено."
        )


@router.message(Command("export"))
async def export_applications(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет доступа.")
        return

    try:
        applications = await get_all_applications()

        if not applications:
            await message.answer(
                "Пока нечего экспортировать."
            )
            return

        excel_file = create_excel_report(applications)

        document = BufferedInputFile(
            excel_file.getvalue(),
            filename="applications.xlsx",
        )

        await message.answer_document(
            document=document,
            caption=(
                "📊 Экспорт заявок завершён!\n"
                f"Всего записей: {len(applications)}"
            ),
        )

    except Exception:
        logging.exception(
            "Ошибка экспорта заявок в Excel"
        )

        await message.answer(
            "Не удалось выполнить экспорт. "
            "Подробности записаны в журнал."
        )


@router.message(Command("backup"))
async def backup_database(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет доступа.")
        return

    try:
        backup_path = await asyncio.to_thread(
            create_backup
        )

        document = FSInputFile(
            backup_path,
            filename=backup_path.name,
        )

        await message.answer_document(
            document=document,
            caption="💾 Резервная копия базы данных",
        )

    except Exception:
        logging.exception(
            "Ошибка создания или отправки резервной копии БД"
        )

        await message.answer(
            "Не удалось создать или отправить резервную копию. "
            "Подробности записаны в журнал."
        )