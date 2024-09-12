import aiosqlite
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from aiogram import F

from dispatcher import dp
from quiz_data import quiz_data

# Зададим имя базы данных
DB_NAME = 'quiz_bot.db'

async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS 
                quiz_state
                (
                user_id INTEGER PRIMARY KEY, 
                question_index INTEGER, 
                score INTEGER DEFAULT 0
                )
        ''')
        await db.commit()

async def update_quiz_index(user_id: int, index: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute(
            "INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)",
            (user_id, index))
        # Сохраняем изменения
        await db.commit()

async def get_quiz_index(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0
            
async def update_score(user_id: int, new_score: int):
    # обновление счётчика правильных ответов
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE quiz_state SET score = ? WHERE user_id = ?",(new_score, user_id))
        await db.commit()

async def get_score(user_id: int) -> int:
    # Функция получения значения счётчика правильных ответов
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT score FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0  # Возвращаем 0, если пользователь не найден

async def get_question(message, user_id):
    # Запрашиваем из базы текущий индекс для вопроса
    current_question_index = await get_quiz_index(user_id)
    # Получаем индекс правильного ответа для текущего вопроса
    correct_index = quiz_data[current_question_index]['correct_option']
    # Получаем список вариантов ответа для текущего вопроса
    opts = quiz_data[current_question_index]['options']

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts, opts[correct_index])
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

def generate_options_keyboard(answer_options, right_answer):
    # cоздаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем 4 Inline кнопки, а точнее Callback-кнопки
    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            # Присваиваем данные для колбэк запроса.
            # Если ответ верный сформируется колбэк-запрос с данными 'right_answer'
            # Если ответ неверный сформируется колбэк-запрос с данными 'wrong_answer'
            callback_data=f"right_answer:{option}" if option == right_answer else f"wrong_answer:{option}")
        )

    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()

@dp.callback_query(F.data.startswith("right_answer:"))
async def right_answer(callback: types.CallbackQuery):
    #выносим ответ пользователя в переменную
    selected_option = callback.data.split(":")[1]

    #редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получение текущего вопроса для данного пользователя
    current_question_index = await get_quiz_index(callback.from_user.id)

    # Получение текущего значения правильных ответов
    current_score = await get_score(callback.from_user.id)

    # Отправляем в чат сообщение, что ответ верный
    await callback.message.answer(f"Ваш ответ: {selected_option}. Верно!")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    current_score += 1
    await update_score(callback.from_user.id, current_score)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        await callback.message.answer(f"Ваш результат: {current_score} правильных ответов из {len(quiz_data)}.")


@dp.callback_query(F.data.startswith("wrong_answer:"))
async def wrong_answer(callback: types.CallbackQuery):
    # выносим ответ пользователя в переменную
    selected_option = callback.data.split(":")[1]

    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получение текущего вопроса для данного пользователя
    current_question_index = await get_quiz_index(callback.from_user.id)

    # Получение текущего значения правильных ответов
    current_score = await get_score(callback.from_user.id)

    correct_option = quiz_data[current_question_index]['correct_option']  # индекс правильного ответа

    # Отправляем в чат сообщение об ошибке с указанием верного ответа
    await callback.message.answer(f"Ваш ответ: {selected_option}. Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    await update_score(callback.from_user.id, current_score)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        await callback.message.answer(f"Ваш результат: {current_score} правильных ответов из {len(quiz_data)}.")

    