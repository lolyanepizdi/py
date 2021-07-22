from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType, ReplyKeyboardRemove
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import *
from states import ProductState, CategoryState
from aiogram.types.chat import ChatActions
from handlers.admin import settings
from loader import dp, db, bot
from filters import IsAdmin
from hashlib import md5
from handlers.user.menu import admin_menu


category_cb = CallbackData('category', 'id', 'action')
product_cb = CallbackData('product', 'id', 'action')

add_product = '➕ Добавить товар'
delete_category = '🗑️ Удалить категорию'


@dp.message_handler(IsAdmin(), text=settings.catalog_settings)
async def process_catalog_settings(message: Message):
    await message.answer('Настройка каталога', reply_markup=back_markup())
    catalog_markup = InlineKeyboardMarkup()

    for idx, title in db.fetchall('SELECT * FROM categories'):

        catalog_markup.add(InlineKeyboardButton(
            title, callback_data=category_cb.new(id=idx, action='view')))

    catalog_markup.add(InlineKeyboardButton(
        '+ Добавить категорию', callback_data='add_category'))

    await message.answer('Настройка категорий:', reply_markup=catalog_markup)


@dp.message_handler(IsAdmin(), text=back_message)
async def process_back_to_menu_catalog(message: Message):
    if message.text == back_message:
        await settings.process_settings(message)


@dp.callback_query_handler(IsAdmin(), category_cb.filter(action='view'))
async def category_callback_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):

    category_idx = callback_data['id']

    products = db.fetchall('''SELECT * FROM products product
    WHERE product.tag = (SELECT title FROM categories WHERE idx=?)''',
                           (category_idx,))

    await query.message.delete()
    await query.answer('Все добавленные товары в эту категорию.')
    await state.update_data(category_index=category_idx)
    await show_products(query.message, products, category_idx)


# category


@dp.callback_query_handler(IsAdmin(), text='add_category')
async def add_category_callback_handler(query: CallbackQuery):
    await query.message.delete()
    await query.message.answer('Название категории?', reply_markup=back_markup())
    await CategoryState.title.set()


@dp.message_handler(IsAdmin(), state=CategoryState.title)
async def set_category_title_handler(message: Message, state: FSMContext):

    category = message.text
    idx = md5(category.encode('utf-8')).hexdigest()
    db.query('INSERT INTO categories VALUES (?, ?)', (idx, category))

    await state.finish()
    await process_catalog_settings(message)


@dp.message_handler(IsAdmin(), text=delete_category)
async def delete_category_handler(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if 'category_index' in data.keys():
            idx = data['category_index']
            db.query(
                'DELETE FROM products WHERE tag IN (SELECT title FROM categories WHERE idx=?)', (idx,))
            db.query('DELETE FROM categories WHERE idx=?', (idx,))

            await message.answer('Готово!')
    await process_catalog_settings(message)


# add product


@dp.message_handler(IsAdmin(), text=add_product)
async def process_add_product(message: Message):

    await ProductState.title.set()

    await message.answer('Название?', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=ProductState.title)
async def process_title_back(message: Message, state: FSMContext):

    await state.finish()
    await process_catalog_settings(message)


@dp.message_handler(IsAdmin(), state=ProductState.title)
async def process_title(message: Message, state: FSMContext):

    async with state.proxy() as data:
        data['title'] = message.text

    await ProductState.body.set()
    await message.answer('Описание?', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=ProductState.body)
async def process_body_back(message: Message, state: FSMContext):

    await ProductState.title.set()

    async with state.proxy() as data:
        await message.answer(f"Изменить название с <b>{data['title']}</b>?", reply_markup=back_markup())


@dp.message_handler(IsAdmin(), state=ProductState.body)
async def process_body(message: Message, state: FSMContext):

    async with state.proxy() as data:
        data['body'] = message.text

    await ProductState.image.set()
    await message.answer('Фото?', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=ProductState.image)
async def process_body_back(message: Message, state: FSMContext):
    await ProductState.body.set()
    await message.answer('Цена?', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), content_types=ContentType.PHOTO, state=ProductState.image)
async def process_image_photo(message: Message, state: FSMContext):

    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = (await bot.download_file(file_info.file_path)).read()

    async with state.proxy() as data:
        data['image'] = downloaded_file

    await ProductState.next()
    await message.answer('Цена?', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), content_types=ContentType.TEXT, state=ProductState.image)
async def process_image_url(message: Message, state: FSMContext):

    if message.text == back_message:

        await ProductState.body.set()

        async with state.proxy() as data:

            await message.answer(f"Изменить описание с <b>{data['body']}</b>?", reply_markup=back_markup())

    else:

        await message.answer('Вам нужно прислать фото товара.')


@dp.message_handler(IsAdmin(), lambda message: not message.text.isdigit(), state=ProductState.price)
async def process_price_invalid(message: Message):

    if message.text == back_message:

        await ProductState.image.set()

        await message.answer("Другое изображение?", reply_markup=back_markup())

    else:

        await message.answer('Укажите цену в виде числа!')


@dp.message_handler(IsAdmin(), lambda message: message.text.isdigit(), state=ProductState.price)
async def process_price(message: Message, state: FSMContext):

    async with state.proxy() as data:

        data['price'] = message.text

        await ProductState.next()
        await message.answer('Количество?', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), lambda message: message.text.isdigit(), state=ProductState.amount)
async def process_amount(message: Message, state: FSMContext):

    async with state.proxy() as data:
        data['amount'] = message.text

        title = data['title']
        body = data['body']
        price = data['price']
        amount = data['amount']

        await ProductState.next()
        text = f'<b>{title}</b>\n\n{body}\n\nЦена: {price}$\n\nКоличество в наличии: {amount} шт.'

        await message.answer_photo(photo=data['image'],
                                   caption=text,
                                   reply_markup=check_markup())


@dp.message_handler(IsAdmin(), lambda message: not message.text.isdigit(), state=ProductState.amount)
async def process_amount_invalid(message: Message, state: FSMContext):

    if message.text == back_message:

        await ProductState.price.set()

        async with state.proxy() as data:
            await message.answer(f"Изменить цену с <b>{data['price']}</b>?", reply_markup=back_markup())
    else:
        await message.answer('Укажите количество товара в виде числа!')


@dp.message_handler(IsAdmin(), text=back_message, state=ProductState.confirm)
async def process_confirm_back(message: Message, state: FSMContext):
    await ProductState.amount.set()
    async with state.proxy() as data:
        await message.answer(f"Изменить количество с <b>{data['amount']}</b>?", reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=all_right_message, state=ProductState.confirm)
async def process_confirm(message: Message, state: FSMContext):

    async with state.proxy() as data:

        title = data['title']
        body = data['body']
        image = data['image']
        price = data['price']
        amount = data['amount']

        tag = db.fetchone(
            'SELECT title FROM categories WHERE idx=?', (data['category_index'],))[0]
        idx = md5(' '.join([title, body, price, amount, tag]
                           ).encode('utf-8')).hexdigest()

        db.query('INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (idx, title, body, image, int(price), int(amount), tag))

    await state.finish()
    await message.answer('Готово!')
    await process_catalog_settings(message)


# delete product


@dp.callback_query_handler(IsAdmin(), product_cb.filter(action='delete'))
async def delete_product_callback_handler(query: CallbackQuery, callback_data: dict):

    product_idx = callback_data['id']
    db.query('DELETE FROM products WHERE idx=?', (product_idx,))
    await query.answer('Удалено!')
    await query.message.delete()


async def show_products(m, products, category_idx):

    await bot.send_chat_action(m.chat.id, ChatActions.TYPING)

    for idx, title, body, image, price, amount, tag in products:

        text = f'<b>{title}</b>\n\n{body}\n\nЦена: {price}$\n\nКоличество в наличии: {amount} шт.'

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            '🗑️ Удалить', callback_data=product_cb.new(id=idx, action='delete')))

        await m.answer_photo(photo=image,
                             caption=text,
                             reply_markup=markup)

    show_markup = ReplyKeyboardMarkup()
    show_markup.add(add_product)
    show_markup.add(delete_category)
    show_markup.add(back_message)

    await m.answer('Хотите что-нибудь изменить?', reply_markup=show_markup)


@dp.message_handler(IsAdmin(), text=menu_message)
async def confirm_menu(message: Message):
    await admin_menu(message)
