from aiogram.types import Message, ReplyKeyboardMarkup
from aiogram.dispatcher import FSMContext
from loader import dp, db, bot
from handlers.user.menu import mail
from filters import IsAdmin
from states import MailState
from handlers.user import menu
from keyboards.default.markups import all_right_message, cancel_message, submit_markup, back_markup, back_message

admin_markup = ReplyKeyboardMarkup()
admin_markup.add(menu.settings, menu.orders, menu.mod_reviews)
admin_markup.add(menu.questions, menu.mail, menu.mod_recrute)


def text_formatter():
    users = db.fetchall('SELECT cid FROM users')
    user_number = len(users)
    if user_number % 100 not in range(12, 15) and user_number % 10 in range(2, 5):
        return f'Сейчас в боте <b>{user_number} пользователя!</b>'
    elif user_number % 100 != 11 and user_number % 10 == 1:
        return f'Сейчас в боте <b>{user_number} пользователь!</b>'
    else:
        return f'Сейчас в боте <b>{user_number} пользователей!</b>'


@dp.message_handler(IsAdmin(), text=mail)
async def cmd_mail(message: Message):
    await MailState.text.set()
    await message.answer(f'''{text_formatter()}
Введите текст для рассылки.''', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=MailState.text)
async def process_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!', reply_markup=admin_markup)
    await state.finish()


@dp.message_handler(IsAdmin(), state=MailState.text)
async def process_text(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    await message.answer('Убедитесь, что все верно.', reply_markup=submit_markup())
    await MailState.next()


@dp.message_handler(text=cancel_message, state=MailState.submit)
async def process_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!', reply_markup=admin_markup)
    await state.finish()


@dp.message_handler(text=all_right_message, state=MailState.submit)
async def process_submit(message: Message, state: FSMContext):
    users = db.fetchall('SELECT cid FROM users')
    await message.answer('Рассылка начата!', reply_markup=admin_markup)
    async with state.proxy() as data:
        for user in users:
            await bot.send_message(user[0], text=data['text'])
        await message.answer(f'''{data['text']}

Рассылка закончена.''', reply_markup=admin_markup)
    await state.finish()
