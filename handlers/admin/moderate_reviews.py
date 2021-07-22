from handlers.user.menu import mod_reviews
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import all_right_message, cancel_message, submit_markup, back_message, back_markup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.types.chat import ChatActions
from states import ModerateReviewState, ChannelState
from loader import dp, db, bot
from filters import IsOper
from handlers.user import menu

oper_markup = ReplyKeyboardMarkup()
oper_markup.add(mod_reviews, menu.questions)
oper_markup.add(menu.mod_recrute)

review_cb = CallbackData('review', 'id', 'action')


@dp.message_handler(IsOper(), text=mod_reviews)
async def process_mod_review(message: Message):

    await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
    reviews = db.fetchall('SELECT * FROM reviews')
    await message.answer('''Это раздел управления отзывами''', reply_markup=back_markup())
    if len(reviews) == 0:
        await message.answer('Нет новых отзывов.', reply_markup=back_markup())
    else:
        for idx, cid, user, category, product_name, review, photo in reviews:
            text = f'''<b>Новый отзыв!</b>

<b>От:</b> @{user}
<b>Категория:</b> {category}
<b>Товар:</b> {product_name}
<b>Отзыв:</b> {review}'''
            answer_markup = InlineKeyboardMarkup()
            answer_markup.add(
                InlineKeyboardButton('Выложить отзыв', callback_data=review_cb.new(id=idx, action='public_review')))
            answer_markup.add(
                InlineKeyboardButton('Удалить отзыв', callback_data=review_cb.new(id=idx, action='delete_review')))
            await message.answer_photo(photo=photo, caption=text, reply_markup=answer_markup)


@dp.message_handler(IsOper(), text=cancel_message, state=ModerateReviewState.channel_id)
async def send_review_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!', reply_markup=oper_markup)
    await state.finish()
    await process_mod_review(message)


@dp.callback_query_handler(IsOper(), review_cb.filter(action='public_review'))
async def process_send_review(query: CallbackQuery, callback_data: dict, state: FSMContext):
    idx = callback_data['id']
    reviews = db.fetchall('SELECT * FROM reviews WHERE idx=?', (idx,))
    print(reviews)
    db.query('DELETE FROM reviews WHERE idx=?', (idx,))
    for _, cid, user, category, product_name, review, photo in reviews:
        text = f'''<b>Новый отзыв!</b>

<b>От:</b> @{user}
<b>Категория:</b> {category}
<b>Товар:</b> {product_name}
<b>Отзыв:</b> {review}'''

        if db.fetchone('SELECT channel_id FROM channels WHERE role=?', ('Для отзывов',)) is None:
            await query.message.answer('Ни один канал еще не подключен к боту.', reply_markup=back_markup())
            await state.finish()
        else:
            channels = db.fetchall('SELECT channel_id FROM channels WHERE role=?', ('Для отзывов',))
            print(channels)
            for channel_id in channels:
                print(channel_id)
                await bot.send_photo(channel_id, photo=photo, caption=text)

        await query.message.answer('Опубликовано!')
        await bot.send_message(cid, 'Ваш отзыв был опубликован.')
        await query.message.delete()

        await state.finish()
        await menu.oper_menu(query.message)


@dp.callback_query_handler(IsOper(), review_cb.filter(action='delete_review'))
async def process_public(query: CallbackQuery, callback_data: dict):

    idx = callback_data['id']
    if db.fetchone('SELECT cid FROM reviews WHERE idx=?', (idx,)) is None:
        await query.message.answer('Произошла ошибка! Удалять нечего.')
    else:
        cid = db.fetchone('SELECT cid FROM reviews WHERE idx=?', (idx,))[0]
        db.query('DELETE FROM reviews WHERE idx=?', (idx,))
        await query.answer('Удалено!')
        await query.message.delete()
        await bot.send_message(cid, 'Ваш отзыв был отклонен.')

