from handlers.user.menu import questions
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import all_right_message, cancel_message, submit_markup, back_markup, back_message
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.chat import ChatActions
from states import AnswerState
from loader import dp, db, bot
from filters import IsOper

question_cb = CallbackData('question', 'cid', 'action')


@dp.message_handler(IsOper(), text=questions)
async def process_questions(message: Message):
    await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
    if db.fetchone('SELECT * FROM questions') is None:
        await message.answer('Нет новых вопросов.', reply_markup=back_markup())
    else:
        quests = db.fetchall('SELECT * FROM questions')
        for cid, question in quests:
            answer_markup = InlineKeyboardMarkup()
            answer_markup.add(InlineKeyboardButton('Ответить', callback_data=question_cb.new(cid=cid, action='answer')))

            await message.answer(question, reply_markup=answer_markup)


@dp.callback_query_handler(IsOper(), question_cb.filter(action='answer'))
async def process_answer(query: CallbackQuery, callback_data: dict, state: FSMContext):

    async with state.proxy() as data:
        data['cid'] = callback_data['cid']

    await query.message.answer('Напиши ответ.', reply_markup=back_markup())
    await AnswerState.answer.set()


@dp.message_handler(IsOper(), text=back_message, state=AnswerState.answer)
async def process_answer_back(message: Message, state: FSMContext):
    await state.finish()
    await process_questions(message)


@dp.message_handler(IsOper(), state=AnswerState.answer)
async def process_submit(message: Message, state: FSMContext):

    async with state.proxy() as data:
        data['answer'] = message.text

    await AnswerState.submit.set()
    await message.answer('Убедитесь, что не ошиблись в ответе.', reply_markup=submit_markup())


@dp.message_handler(IsOper(), text=cancel_message, state=AnswerState.submit)
async def process_send_answer(message: Message):
    await AnswerState.answer.set()
    await message.answer('Изменить текст ответа?', reply_markup=back_markup())


@dp.message_handler(IsOper(), text=all_right_message, state=AnswerState.submit)
async def process_send_answer(message: Message, state: FSMContext):
    async with state.proxy() as data:
        answer = data['answer']
        cid = data['cid']

        question = db.fetchone('SELECT question FROM questions WHERE cid=?', (cid,))[0]
        db.query('DELETE FROM questions WHERE cid=?', (cid,))
        text = f'''<b>Вопрос:</b> {question}
<b>Ответ:</b> {answer}'''

    await message.answer('Отправлено!')
    await bot.send_message(cid, text)

    await state.finish()
    await process_questions(message)
