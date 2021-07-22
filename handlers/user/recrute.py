from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.default.markups import all_right_message, submit_markup, back_message
from aiogram.types import Message
from states import WorkState
from filters import IsUser
from loader import dp, db, bot
from handlers.user import menu
from handlers.user.menu import recrute
from hashlib import md5

markup = ReplyKeyboardMarkup()
markup.add(menu.catalog)
markup.add(menu.cart, menu.delivery_status, menu.reviews)
markup.add(menu.referal, recrute, menu.contacts)

work_cb = CallbackData('work', 'id', 'action')

work_back_markup = ReplyKeyboardMarkup()
work_back_markup.add(back_message)

work_markup = ReplyKeyboardMarkup()
work_markup.add('Заполнить анкету', back_message)


@dp.message_handler(IsUser(), text=recrute)
async def process_review(message: Message):
    await message.answer('Привет! Это раздел вакансий. Тут ты можешь оставить свою анкету и устроиться к нам на работу.',
                         reply_markup=work_markup)


@dp.message_handler(IsUser(), text='Заполнить анкету')
async def add_review_process(message: Message):
    await WorkState.form.set()
    await message.answer('''Напишите ответы на эти вопросы в таком формате (каждый вопрос обязательно с новой строки!):
1.Каким залогом Вы располагаете ?
1.1. Пол и возраст.
2. Соблюдаете ли анонимность и безопасность в сети? Расскажите как!
3. Наличие опыта работы кладменом, можете ли подтвердить свой стаж?
4.Права и личный автомобиль, стаж вождения?
5.Город и район проживания.
6.Употребляете ли какие-то ПАВ? Насколько часто?
7.Какой график работы больше всего подходит для Вас? Насколько готовы обеспечить соблюдение режима? 
8.Количество кладов, выполнение которых можете гарантировать?
9.Вас остановили для проверки документов, а на руках несколько закладок, готовых к реализации. Что будете делать, если полиция решит провести личный досмотр?
10.Поделитесь с нами примером оптимального описания своего клада.''', reply_markup=work_back_markup)


@dp.message_handler(IsUser(), text=back_message, state=WorkState.form)
async def process_work_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!', reply_markup=markup)
    await state.finish()


@dp.message_handler(IsUser(), state=WorkState.form)
async def set_work_text_handler(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['form'] = message.text
    if len(data['form']) >= 500:
        await message.answer('Хотите отправить анкету?', reply_markup=submit_markup())
        await WorkState.next()
    else:
        await message.answer('Слишком короткая анкета! Минимальное кол-во символов: 500.', reply_markup=work_back_markup)


@dp.message_handler(IsUser(), text=all_right_message, state=WorkState.submit)
async def process_work_submit(message: Message, state: FSMContext):
    cid = message.chat.id
    username = message.from_user.username
    async with state.proxy() as data:
        work_form = data['form']
        data['idx'] = md5(' '.join([str(cid), username, work_form]).encode('utf-8')).hexdigest()
        db.query('INSERT INTO work VALUES (?, ?, ?, ?)',
                 (data['idx'], cid, username, work_form))

        await message.answer('Отправлено на пре-модерацию!', reply_markup=markup)

        text = f'''Новая анкета!
От: <b>@{username}</b>
<b>Текст:</b> 
{work_form}'''
        answer_markup = InlineKeyboardMarkup()
        answer_markup.add(InlineKeyboardButton('Связаться', url=f'https://t.me/{username}?start='))
        answer_markup.add(InlineKeyboardButton('Удалить анкету', callback_data=work_cb.new(id=data['idx'], action='delete_form')))
        admins = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Админ',))[0]
        opers = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Оператор',))[0]
        for cid in admins and cid in opers:
            await bot.send_message(cid, text=text, reply_markup=answer_markup)
    await state.finish()
