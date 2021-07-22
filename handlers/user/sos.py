from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.default.markups import all_right_message, cancel_message, submit_markup, back_message, back_markup
from aiogram.types import Message
from states import SosState
from filters import IsUser
from loader import dp, db, bot
from handlers.user import menu

markup = ReplyKeyboardMarkup()
markup.add(menu.catalog)
markup.add(menu.cart, menu.delivery_status, menu.reviews)
markup.add(menu.referal, menu.recrute, menu.contacts)

question_cb = CallbackData('question', 'cid', 'action')


@dp.message_handler(IsUser(), commands='sos')
async def cmd_sos(message: Message):

    await SosState.question.set()
    await message.answer('В чем суть проблемы? Опишите как можно детальнее и администратор обязательно вам ответит.', reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=SosState.question)
async def process_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!')
    await state.finish()
    await menu.user_menu(message)


@dp.message_handler(IsUser(), state=SosState.question)
async def process_question(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['question'] = message.text

    await message.answer(f'''Убедитесь, что все верно:
    
{data["question"]}''', reply_markup=submit_markup())
    await SosState.submit.set()


@dp.message_handler(IsUser(), text=cancel_message, state=SosState.submit)
async def process_sos_cancel(message: Message):
    await SosState.question.set()
    await message.answer('Хотите изменить текст вопроса?', reply_markup=back_markup())


@dp.message_handler(IsUser(), text=all_right_message, state=SosState.submit)
async def process_submit(message: Message, state: FSMContext):
    cid = message.chat.id
    if db.fetchone('SELECT * FROM questions WHERE cid=?', (cid,)) is None:
        async with state.proxy() as data:
            db.query('INSERT INTO questions VALUES (?, ?)',
                     (cid, data['question']))
        await message.answer('Отправлено!')

        text = f"<b>Вопрос:</b> {data['question']}"
        answer_markup = InlineKeyboardMarkup()
        answer_markup.add(InlineKeyboardButton('Ответить', callback_data=question_cb.new(cid=cid, action='answer')))
        admins = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Админ',))[0]
        if db.fetchone('SELECT cid FROM admins WHERE role=?', ('Оператор',)) is None:
            for cid in admins:
                await bot.send_message(cid, text=text, reply_markup=answer_markup)
        else:
            opers = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Оператор',))[0]
            for cid in admins and cid in opers:
                await bot.send_message(cid, text=text, reply_markup=answer_markup)
    else:
        await message.answer('Превышен лимит на количество задаваемых вопросов.')

    await state.finish()
    await menu.user_menu(message)
