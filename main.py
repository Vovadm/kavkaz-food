import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from sqlalchemy import text

from handlers import register_handlers
from parsing import AsyncSessionLocal


async def keep_db_connection_alive():
    while True:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            print("reconnect")
        await asyncio.sleep(300)


async def main():
    load_dotenv()
    bot = Bot(token=os.getenv("TOKEN"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    register_handlers(dp)

    asyncio.create_task(keep_db_connection_alive())
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
