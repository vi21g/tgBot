import asyncio
import logging
from aiogram import Bot

# import project moduls
from database import create_table
from handlers import cmd_start, cmd_quiz, new_quiz
from dispatcher import dp
from token_1 import API_TOKEN

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token=API_TOKEN)


# Запуск процесса поллинга новых апдейтов
async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())