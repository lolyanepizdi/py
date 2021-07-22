from aiogram.types import Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from loader import dp, db
from filters import IsAdmin, IsUser, IsOper, IsCura
import json

catalog = '🛍️ Каталог'
cart = '🛒 Корзина'
delivery_status = '🚚 Статус заказа'
reviews = '📝 Отзывы'
referal = '💰 Рефералка'
recrute = '💸 Работа'
contacts = '🛎 Контакты'

mod_reviews = '📖 Отзывы'
mod_recrute = '💵 Работа'
mail = '📨 Рассылка'
settings = '⚙️ Настройки'
orders = '🚚 Заказы'
questions = '❓ Вопросы'


@dp.message_handler(IsAdmin(), commands=['admin', 'start'])
async def admin_menu(message: Message):
    admin_markup = ReplyKeyboardMarkup()
    admin_markup.add(settings, orders, mod_reviews)
    admin_markup.add(questions, mail, mod_recrute)
    first_name = message.chat.first_name
    await message.answer(f'''
Привет, <b>{first_name}!</b> 👋
🤖 Я бот магазина Marrakesh.        
💰 Покупка товаров возможна через bitcoin и KUNA Code.''', reply_markup=admin_markup)


@dp.message_handler(IsUser(), commands=['start', 'menu'])
async def user_menu(message: Message):
    cid = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    ref_users = []
    ref_buyers = []
    if db.fetchone('SELECT first_name FROM users WHERE cid=?', (cid,)) is None:
        if db.fetchone('SELECT first_name FROM admins WHERE cid=?', (cid,)) is None:
            db.query('INSERT INTO referral VALUES (?, ?, ?, ?, ?)',
                     (cid, username, json.dumps(ref_users), json.dumps(ref_buyers), 0))
        else:
            await admin_menu(message)

        if len(message.text.split()) > 1 and 'start' in message.text:
            referral = message.text.split()[1]
            ref_cid = db.fetchone('SELECT cid FROM users WHERE username=?', (referral,))[0]
            if referral != username and cid not in ref_users:
                ref_users.append(cid)

            if db.fetchone('SELECT bonus FROM referral WHERE username=?', (referral,)) is None:
                db.query('INSERT INTO referral VALUES (?, ?, ?, ?, ?)', (ref_cid, referral, json.dumps(ref_users), json.dumps(ref_buyers), 0))
            else:
                db.query('UPDATE referral SET ref_users=? WHERE username=? AND cid=?', (json.dumps(ref_users), referral, ref_cid))
                db.query('INSERT or REPLACE INTO users VALUES (?, ?, ?, ?)', (cid, username, first_name, referral))
        else:
            db.query('INSERT or REPLACE INTO referral VALUES (?, ?, ?, ?, ?)', (cid, username, json.dumps(ref_users), json.dumps(ref_buyers), 0))
            db.query('INSERT or REPLACE INTO users VALUES (?, ?, ?, ?)', (cid, username, first_name, None))
    else:
        user = db.fetchone('SELECT * FROM users WHERE cid=?', (cid,))
        username = user[1]
        if db.fetchone('SELECT bonus FROM referral WHERE username=?', (username,)) is None:
            db.query('INSERT INTO referral VALUES (?, ?, ?, ?, ?)', (cid, username, json.dumps(ref_users), json.dumps(ref_buyers), 0))

    user_markup = ReplyKeyboardMarkup()
    user_markup.add(catalog)
    user_markup.add(cart, delivery_status, reviews)
    user_markup.add(referal, recrute, contacts)

    await message.answer(f'''
Привет, {first_name}! 👋
🤖 Я бот магазина Marrakesh.    
💰 Покупка товаров возможна через bitcoin и KUNA Code.
❓ Возникли вопросы? Не проблема! Команда /sos поможет связаться с админами. 
Мы постараемся откликнуться как можно скорее.''', reply_markup=user_markup)



@dp.message_handler(IsCura(), commands=['cura', 'start'])
async def cura_menu(message: Message):
    cura_markup = ReplyKeyboardMarkup()
    cura_markup.add(orders)
    first_name = message.chat.first_name
    await message.answer(f'''
Привет, <b>{first_name}</b>! 👋
🤖 Я бот магазина Marrakesh.        
💰 Покупка товаров возможна через bitcoin и KUNA Code.
✏️ Ввести ТТН ваших заказов можно в подменю "{orders}".''', reply_markup=cura_markup)


@dp.message_handler(IsOper(), commands=['oper', 'start'])
async def oper_menu(message: Message):
    oper_markup = ReplyKeyboardMarkup()
    oper_markup.add(mod_reviews, questions)
    oper_markup.add(mod_recrute)
    first_name = message.chat.first_name
    await message.answer(f'''
Привет, <b>{first_name}</b>! 👋
🤖 Я бот магазина Marrakesh.        
💰 Покупка товаров возможна через bitcoin и KUNA Code.''', reply_markup=oper_markup)


@dp.message_handler(IsUser(), text=contacts)
async def contacts_text(message: Message):
    cid = message.chat.id
    first_name = db.fetchone('SELECT first_name FROM users WHERE cid=?', (cid,))[0]
    user_markup = ReplyKeyboardMarkup()
    user_markup.add(catalog)
    user_markup.add(cart, delivery_status, reviews)
    user_markup.add(referal, recrute, contacts)

    await message.answer(f'''
 Привет, <b>{first_name}</b>! 👋
Это раздел наших контактов.''')
    if db.fetchone('SELECT username FROM contacts WHERE role=?', ('Оператор',)) is None and db.fetchone('SELECT username FROM contacts WHERE role=?', ('Админ',)) is None:
        await message.answer('Контакты еще не были добавлены в бота.', reply_markup=user_markup)

    elif db.fetchone('SELECT username FROM contacts WHERE role=?', ('Оператор',)) is None:
        admin = db.fetchone('SELECT username FROM contacts WHERE role=?', ('Админ',))[0]
        contact_markup = InlineKeyboardMarkup()
        contact_markup.add(InlineKeyboardButton('Админ', url=f'https://t.me/{admin}?start='))
        await message.answer('С нами можно связаться по этим контактам:', reply_markup=contact_markup)

    elif db.fetchone('SELECT username FROM contacts WHERE role=?', ('Админ',)) is None:
        oper = db.fetchone('SELECT username FROM contacts WHERE role=?', ('Оператор',))[0]
        contact_markup = InlineKeyboardMarkup()
        contact_markup.add(InlineKeyboardButton('Оператор', url=f'https://t.me/{oper}?start='))
        await message.answer('С нами можно связаться по этим контактам:', reply_markup=contact_markup)

    else:
        admin = db.fetchone('SELECT username FROM contacts WHERE role=?', ('Админ',))[0]
        oper = db.fetchone('SELECT username FROM contacts WHERE role=?', ('Оператор',))[0]

        contact_markup = InlineKeyboardMarkup()
        contact_markup.add(InlineKeyboardButton('Оператор', url=f'https://t.me/{oper}?start='))
        contact_markup.add(InlineKeyboardButton('Админ', url=f'https://t.me/{admin}?start='))

        await message.answer('С нами можно связаться по этим контактам:', reply_markup=contact_markup)
