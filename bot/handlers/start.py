from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.keyboards import main_keyboard


router = Router()


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "Привет! 👋\n\n"
        "Я помогу оформить заявку.\n"
        "Нажми кнопку ниже, чтобы начать.",
        reply_markup=main_keyboard
    )