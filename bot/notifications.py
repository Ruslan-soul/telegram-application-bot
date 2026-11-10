
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from bot.config import ADMIN_IDS


async def notify_admins(
    bot: Bot,
    application_id: int,
    data: dict
):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Открыть заявку",
                    callback_data=f"admin:view:{application_id}"
                )
            ]
        ]
    )

    text = (
        f"🔔 НОВАЯ ЗАЯВКА №{application_id}\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🛠 Услуга: {data['service']}\n"
        f"💬 Комментарий: {data['comment']}\n\n"
        "📌 Статус: 🆕 Новая"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=keyboard
            )

        except TelegramAPIError:
            logging.exception(
                "Не удалось отправить уведомление администратору %s",
                admin_id
            )
