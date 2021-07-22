from handlers.user.menu import mod_recrute
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import back_message, back_markup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.types.chat import ChatActions
from loader import dp, db, bot
from filters import IsOper
from handlers.user import menu
from handlers.admin.settings import process_settings


admin_markup = ReplyKeyboardMarkup()
admin_markup.add(menu.settings, menu.orders, menu.mod_reviews)
admin_markup.add(menu.questions, menu.mail, menu.mod_recrute)

work_cb = CallbackData('work', 'id', 'action')


@dp.message_handler(IsOper(), text=mod_recrute)
async def process_mod_recrute(message: Message):
    await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
    forms = db.fetchall('SELECT * FROM work')
    if len(forms) == 0:
        await message.answer('Нет новых анкет.', reply_markup=back_markup())
    else:
        for form in forms:
            idx = form[0]
            username = form[2]
            form_text = form[3]
            text = f'''
От: <b>@{username}</b>
<b>Текст:</b>
{form_text}'''
            answer_markup = InlineKeyboardMarkup()
            answer_markup.add(InlineKeyboardButton('Связаться', url=f'https://t.me/{username}?start='))
            answer_markup.add(
                InlineKeyboardButton('Удалить анкету', callback_data=work_cb.new(id=idx, action='delete_form')))
            await message.answer(text, reply_markup=answer_markup)


@dp.message_handler(IsOper(), text=back_message)
async def process_mod_recrute_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!', reply_markup=admin_markup)
        await process_settings(message)


@dp.callback_query_handler(IsOper(), work_cb.filter(action='delete_form'))
async def process_delete(query: CallbackQuery, callback_data: dict):

    idx = callback_data['id']
    cid = db.fetchone('SELECT cid FROM work WHERE idx=?', (idx,))[0]
    db.query('DELETE FROM work WHERE idx=?', (idx,))
    await query.answer('Удалено!')
    await query.message.delete()
    await bot.send_message(cid, 'Ваша анкета была отклонена.')
