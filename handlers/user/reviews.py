from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ContentType
from keyboards.default.markups import all_right_message, back_message, check_markup, back_markup
from aiogram.types import Message
from states import ReviewState
from filters import IsUser
from loader import dp, db, bot
from handlers.user import menu
from handlers.user.menu import reviews
from hashlib import md5

markup = ReplyKeyboardMarkup()
markup.add(menu.catalog)
markup.add(menu.cart, menu.delivery_status, reviews)
markup.add(menu.referal, menu.recrute, menu.contacts)

review_cb = CallbackData('review', 'id', 'action')
review_category_cb = CallbackData('review_category', 'id', 'action')
review_product_cb = CallbackData('review_product', 'id', 'action')

review_back_markup = ReplyKeyboardMarkup()
review_back_markup.add(back_message)

review_markup = ReplyKeyboardMarkup()
review_markup.add('Оставить отзыв', 'Читать все отзывы')
review_markup.add(back_message)


@dp.message_handler(IsUser(), text=reviews)
async def process_review(message: Message):
    await message.answer('Привет! Это раздел отзывов. Тут ты можешь оставить свой отзыв или почитать отзывы других.', reply_markup=review_markup)


@dp.message_handler(IsUser(), text='Оставить отзыв')
async def add_category_process(message: Message):
    cid = message.from_user.id
    buyer = db.fetchone('SELECT username FROM buyers WHERE cid=?', (cid,))
    if buyer is None:
        await message.answer('Вы не сделали ни одной покупки с этого аакаунта, поэтому не можете оставить отзыв!',
                             reply_markup=review_back_markup)
    else:
        await ReviewState.category.set()
        await message.answer('Выберите категорию товара, о котором хотите написать отзыв.', reply_markup=review_back_markup)
        if db.fetchall('SELECT * FROM categories') is None:
            await message.answer('В этом магазине еще не созданы категории!')
        else:
            categories = db.fetchall('SELECT * FROM categories')
            cats_markup = InlineKeyboardMarkup()
            for idx, title in categories:
                cats_markup.add(InlineKeyboardButton(title, callback_data=review_category_cb.new(id=idx, action='copy')))
            await message.answer('Доступные категории:', reply_markup=cats_markup)


@dp.callback_query_handler(IsUser(), review_category_cb.filter(action='copy'), state=ReviewState.category)
async def add_review_category_callback(query: CallbackQuery, callback_data: dict, state: FSMContext):
    idx = callback_data['id']
    async with state.proxy() as data:
        data['category'] = db.fetchone('SELECT title FROM categories WHERE idx=?', (idx,))[0]
    if db.fetchone('SELECT title FROM products WHERE tag=?', (data['category'],)) is None:
        await query.message.answer('Товаров в этой категории нет!', reply_markup=review_back_markup)
    else:
        await ReviewState.product_name.set()
        products = db.fetchall('SELECT * FROM products WHERE tag=?', (data['category'],))
        for idx, title, _, _, _, _, _, in products:
            review_product_markup = InlineKeyboardMarkup()
            review_product_markup.add(InlineKeyboardButton(title, callback_data=review_product_cb.new(id=idx, action='copy')))
        await query.message.answer('Выберите название товара, на который вы хотите написать отзыв:', reply_markup=review_product_markup)


@dp.callback_query_handler(IsUser(), review_product_cb.filter(action='copy'), state=ReviewState.product_name)
async def add_review_product_callback(query: CallbackQuery, callback_data: dict, state: FSMContext):
    idx = callback_data['id']
    async with state.proxy() as data:
        data['product_name'] = db.fetchone('SELECT title FROM products WHERE idx=?', (idx,))[0]
    await ReviewState.text.set()
    await query.message.answer('Напишите свой отзыв (не менее 300 символов).', reply_markup=review_back_markup)


@dp.message_handler(IsUser(), text=back_message, state=ReviewState.text)
async def process_review_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!', reply_markup=markup)
    await state.finish()


@dp.message_handler(IsUser(), state=ReviewState.text)
async def set_review_text_handler(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    if len(data['text']) < 300:
        await message.answer('Длина отзыва слишком маленькая!')
    else:
        await message.answer('Прикрепите фото товара, который вы получили.', reply_markup=review_back_markup)
        await ReviewState.photo.set()


@dp.message_handler(IsUser(), content_types=ContentType.PHOTO, state=ReviewState.photo)
async def process_review_photo(message: Message, state: FSMContext):

    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)

    async with state.proxy() as data:
        data['photo'] = downloaded_file.read()
        category = data['category']
        product_name = data['product_name']
        text = data['text']

        body = f'''Убедитесь что все верно:
        
<b>Категория:</b> {category}
<b>Товар:</b> {product_name}
<b>Отзыв: </b> {text}'''

        await message.answer_photo(photo=data['photo'],
                                   caption=body,
                                   reply_markup=check_markup())
        await ReviewState.submit.set()


@dp.message_handler(IsUser(), content_types=ContentType.TEXT, state=ReviewState.photo)
async def process_photo_url_invalid(message: Message):
    if message.text == back_message:
        await ReviewState.text.set()
        await message.answer(f"Изменить текст отзыва?", reply_markup=back_markup())
    else:
        await message.answer('Вам нужно прислать фото товара.')


@dp.message_handler(IsUser(), text=all_right_message, state=ReviewState.submit)
async def process_review_submit(message: Message, state: FSMContext):
    cid = message.chat.id
    username = db.fetchone('SELECT username FROM users WHERE cid=?', (cid,))[0]
    async with state.proxy() as data:
        category = data['category']
        product_name = data['product_name']
        photo = data['photo']
        text = data['text']
        data['idx'] = md5(' '.join([str(cid), username, text]).encode('utf-8')).hexdigest()
    db.query('INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?)', (data['idx'], cid, username, category, product_name, text, photo))

    await message.answer('Отправлено на пре-модерацию!')
    text = f'''Новый отзыв!
    
<b>От:</b> @{username}
<b>Категория:</b> {category}
<b>Товар:</b> {product_name}
<b>Отзыв:</b> {text}'''
    answer_markup = InlineKeyboardMarkup()
    answer_markup.add(InlineKeyboardButton('Выложить отзыв', callback_data=review_cb.new(id=data['idx'],
                                                                                         action='public_review')))
    answer_markup.add(InlineKeyboardButton('Удалить отзыв', callback_data=review_cb.new(id=data['idx'],
                                                                                        action='delete_review')))
    admins = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Админ',))[0]
    if db.fetchone('SELECT cid FROM admins WHERE role=?', ('Оператор',)) is None:
        for cid in admins:
            await bot.send_photo(cid, photo=photo, caption=text, reply_markup=answer_markup)
    else:
        opers = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Оператор',))[0]
        for cid in admins and cid in opers:
            await bot.send_photo(cid, photo=photo, caption=text, reply_markup=answer_markup)

    await state.finish()
    await menu.user_menu(message)


@dp.message_handler(IsUser(), text='Читать все отзывы')
async def process_read_reviews(message: Message):
    if db.fetchone('SELECT channel_username FROM channels WHERE role=?', ('Для отзывов',)) is None:
        await message.answer('Канал для отзывов еще не был подключен', reply_markup=review_markup)
    else:
        rw_channel_markup = InlineKeyboardMarkup()
        channel_users = db.fetchall('SELECT channel_username FROM channels WHERE role=?', ('Для отзывов',))[0]
        for channel_user in channel_users:
            rw_channel_markup.add(InlineKeyboardButton(f'Перейти на канал @{channel_user}', url=f'https://t.me/{channel_user}?start='))
        await message.answer('Все отзывы вы можете прочитать тут:', reply_markup=rw_channel_markup)
