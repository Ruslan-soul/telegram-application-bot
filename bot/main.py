import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from bot.config import BOT_TOKEN, BASE_DIR
from bot.database.db import init_db
from bot.handlers import start, application, admin


def setup_logging():
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        logs_dir / "bot.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[
            logging.StreamHandler(),
            file_handler
        ],
        force=True
    )


async def error_handler(event: ErrorEvent):
    logging.error(
        "Необработанная ошибка Telegram-бота",
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__
        )
    )

    return True


async def main():
    setup_logging()

    logging.info("Запуск бота...")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.errors.register(error_handler)

    try:
        await init_db()
        logging.info("База данных готова!")

        dp.include_router(start.router)
        dp.include_router(application.router)
        dp.include_router(admin.router)

        logging.info("Бот запущен!")

        await dp.start_polling(bot)

    except Exception:
        logging.exception("Критическая ошибка при работе бота")
        raise

    finally:
        await bot.session.close()
        logging.info("Бот остановлен.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())