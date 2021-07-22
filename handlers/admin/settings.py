from data.config import ADMIN_ID
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from keyboards.default.markups import all_right_message, cancel_message, submit_markup, back_message, back_markup
from aiogram.types import Message
from states import AdminState, SetBonusState, ChannelState, BTCConfigState, KunaConfigState, ContactState
from filters import IsAdmin
from loader import dp, db, bot
from handlers.user import menu
from handlers.user.menu import settings
from hashlib import md5

settings_cb = CallbackData('setting', 'cid', 'action')
btc_setting_cb = CallbackData('btc', 'id', 'action')
kuna_setting_cb = CallbackData('kuna', 'id', 'action')
bonus_setting_cb = CallbackData('bonus', 'id', 'action')
channel_setting_cb = CallbackData('channel', 'id', 'action')
contacts_setting_cb = CallbackData('contact', 'cid', 'action')

admin_markup = ReplyKeyboardMarkup()
admin_markup.add(menu.settings, menu.orders, menu.mod_reviews)
admin_markup.add(menu.questions, menu.mail, menu.mod_recrute)

oper_markup = ReplyKeyboardMarkup()
oper_markup.add(menu.mod_reviews, menu.questions)
oper_markup.add(menu.mod_recrute)

cura_markup = ReplyKeyboardMarkup()
cura_markup.add(menu.orders)

user_markup = ReplyKeyboardMarkup()
user_markup.add(menu.catalog)
user_markup.add(menu.cart, menu.delivery_status, menu.reviews)
user_markup.add(menu.referal, menu.recrute, menu.contacts)

catalog_settings = 'Настройка каталога'
admin_settings = 'Настройка списка админов'
pay_settings = 'Настройка платежной системы'
chat_settings = 'Бот в каналах'
bonus_settings = 'Бонусы'
contact_settings = 'Настройка контактов'


@dp.message_handler(IsAdmin(), text=settings)
async def process_settings(message: Message):
    settings_markup = ReplyKeyboardMarkup()
    settings_markup.add(catalog_settings, admin_settings, contact_settings)
    settings_markup.add(pay_settings, chat_settings, bonus_settings)
    settings_markup.add(back_message)

    await message.answer('Что бы вы хотели изменить?', reply_markup=settings_markup)


@dp.message_handler(IsAdmin(), text=back_message)
async def process_settings_back(message: Message):
    await menu.admin_menu(message)

# Настройка списков админов


@dp.message_handler(IsAdmin(), text=admin_settings)
async def process_admin_settings(message: Message):
    edit_markup = ReplyKeyboardMarkup()
    edit_markup.add('Добавить админа', back_message)
    if db.fetchone('SELECT * FROM admins WHERE NOT cid=?', (ADMIN_ID,)) is None:
        await message.answer('Вы единственный администратор.', reply_markup=edit_markup)
    else:
        admins = db.fetchall('SELECT * FROM admins WHERE NOT cid=?', (ADMIN_ID,))
        for cid, username, first_name, role in admins:
            await message.answer('Список админов:', reply_markup=edit_markup)
            adminlist_markup = InlineKeyboardMarkup()
            adminlist_markup.add(InlineKeyboardButton(f'Удалить {role.lower()}а', callback_data=settings_cb.new(cid=cid, action='delete_admin')))
            await message.answer(f'''Данные админа:
            
<b>User ID:</b> {cid}
<b>Username:</b> {username}
<b>First Name:</b> {first_name}
<b>Роль: </b> {role}''', reply_markup=adminlist_markup)


@dp.message_handler(IsAdmin(), text=back_message)
async def process_back_admin_settings(message: Message):
    await process_settings(message)


@dp.message_handler(IsAdmin(), text='Добавить админа')
async def process_add_admin(message: Message):
    await AdminState.info.set()
    await message.answer('''Перешлите любое сообщение нового админа в чат с ботом.
Он ОБЯЗАТЕЛЬНО должен быть юзером бота!''', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=AdminState.info)
async def admin_cancel(message: Message, state: FSMContext):
    if message.text == back_message:
        await state.finish()
        await process_admin_settings(message)


@dp.message_handler(IsAdmin(), state=AdminState.info)
async def process_admin_info(message: Message, state: FSMContext):
    if message.forward_from is None:
        first_name = message.forward_sender_name
    else:
        first_name = message.forward_from.first_name

    if db.fetchone('SELECT * FROM users WHERE first_name=?', (first_name,)) is None:
        await message.answer('Пользователь не является юзером бота.')

    else:
        admin = db.fetchone('SELECT * FROM users WHERE first_name=?', (first_name,))
        async with state.proxy() as data:
            data['cid'] = admin[0]
            data['username'] = admin[1]
            data['first_name'] = first_name

        await message.answer(f'''Убедитесь, что все правильно:
        
<b>ID:</b> {data['cid']}
<b>Username:</b> {data['username']}
<b>First Name:</b> {first_name}''', reply_markup=submit_markup())
        await AdminState.role.set()


@dp.message_handler(IsAdmin(), text=cancel_message, state=AdminState.role)
async def process_admin_info_cancel(message: Message, state: FSMContext):
    if message.text == cancel_message:
        await state.finish()
        await process_add_admin(message)


@dp.message_handler(IsAdmin(), text=all_right_message, state=AdminState.role)
async def process_role_admin(message: Message):
    role_markup = ReplyKeyboardMarkup()
    role_markup.add('Курьер', 'Оператор', 'Админ')
    role_markup.add(back_message)
    await message.answer('Выберите роль админа в боте', reply_markup=role_markup)
    await AdminState.submit.set()


@dp.message_handler(IsAdmin(), text=back_message, state=AdminState.submit)
async def admin_role_cancel(message: Message):
    if message.text == back_message:
        await AdminState.role.set()


@dp.message_handler(IsAdmin(), lambda message: message.text in ['Курьер', 'Оператор', 'Админ'], state=AdminState.submit)
async def confirm_process_admin(message: Message, state: FSMContext):
    async with state.proxy() as data:
        admins = db.fetchall('SELECT * FROM admins')
        cid = int(data['cid'])
        username = data['username']
        first_name = data['first_name']
        role = message.text
        if role == 'Курьер':
            markup = cura_markup
        if role == 'Оператор':
            markup = oper_markup
        if role == 'Админ':
            markup = admin_markup
    if message.text == role:
        if cid in admins:
            await message.answer(f'{role} <b>{first_name}</b> уже есть!')
            await state.finish()
            await process_admin_settings(message)
        else:
            db.query('INSERT INTO admins VALUES (?, ?, ?, ?)', (cid, username, first_name, role))
            db.query('DELETE FROM users WHERE cid=?', (cid,))
            await message.answer(f'{role} <b>{first_name}</b> успешно добавлен в базу!')
            await bot.send_message(cid, f'Поздравляем, теперь вы один из {role.lower()}ов бота.', reply_markup=markup)
            await state.finish()
            await process_admin_settings(message)


@dp.callback_query_handler(IsAdmin(), settings_cb.filter(action='delete_admin'))
async def process_delete_admin(query: CallbackQuery, callback_data: dict):
    del_cid = callback_data['cid']
    current_cid = query.message.from_user.id
    if del_cid != current_cid:
        if db.fetchone('SELECT * FROM admins WHERE cid=?', (del_cid,)) is not None:
            admin = db.fetchall('SELECT * FROM admins WHERE cid=?', (del_cid,))
            for cid, username, first_name, role in admin:
                db.query('INSERT or REPLACE INTO users VALUES (?, ?, ?, ?)', (cid, username, first_name, None))
                db.query('DELETE FROM admins WHERE cid=?', (cid,))
                await query.answer('Удалено!')
                await query.message.delete()
                await bot.send_message(del_cid, f'Вы больше не {role.lower()} бота!')
                await menu.user_menu(query.message)
    elif del_cid == current_cid:
        await query.message.answer('Самого себя удалить невозможно!')
        await process_admin_settings(query.message)
    elif del_cid == ADMIN_ID:
        await query.message.answer('Главного админа удалить невозможно!')
        await process_admin_settings(query.message)


# Настройка платежки


@dp.message_handler(IsAdmin(), text=pay_settings)
async def process_pay_settings(message: Message):
    pay_markup = ReplyKeyboardMarkup()
    pay_markup.add('Настройка BTC-кошелька', 'Настройка KUNA-кошелька')
    pay_markup.add(back_message)
    await message.answer('Выберите, какую платежку хотите настроить.', reply_markup=pay_markup)


@dp.message_handler(IsAdmin(), text=back_message)
async def process_pay_settings_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_settings(message)


# Настройка BTC-кошелька


@dp.message_handler(IsAdmin(), text='Настройка BTC-кошелька')
async def process_btc_config(message: Message):
    await BTCConfigState.admin_address.set()
    if db.fetchone('SELECT admin_address FROM btc_config') is None:
        await message.answer('''На данный момент, ни один адрес BTC для поступления средств не был добавлен.
Введите номер адреса, на который желаете получать прибыль от продаж.''', reply_markup=back_markup())
    else:
        await message.answer('Зарегистрированные адреса BTC', reply_markup=back_markup())
        address_list = db.fetchall('SELECT * FROM btc_config')
        btc_markup = InlineKeyboardMarkup()
        for idx, address_num in address_list:
            btc_markup.add(InlineKeyboardButton('Удалить', callback_data=btc_setting_cb.new(id=idx, action='del_address')))

            await message.answer(f'<b>Номер адреса:</b> {address_num}', reply_markup=btc_markup)
        await message.answer('Введите номер адреса, на который желаете получать прибыль от продаж.', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=BTCConfigState.admin_address)
async def process_btc_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_settings(message)


@dp.message_handler(IsAdmin(), state=BTCConfigState.admin_address)
async def process_btc_address(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['address_num'] = message.text
        data['idx'] = md5(' '.join(data['address_num']).encode('utf-8')).hexdigest()[:5]
    await message.answer(f'''Убедитесь, что все верно.
<b>Номер адреса BTC:</b> {data['address_num']}''', reply_markup=submit_markup())
    await BTCConfigState.submit.set()


@dp.message_handler(IsAdmin(), text=cancel_message, state=BTCConfigState.submit)
async def process_btc_cancel(message: Message, state: FSMContext):
    if message.text == cancel_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_settings(message)


@dp.message_handler(IsAdmin(), text=all_right_message, state=BTCConfigState.submit)
async def process_btc_submit(message: Message, state: FSMContext):
    async with state.proxy() as data:
        address_num = data['address_num']
        idx = data['idx']

        if db.fetchone('SELECT admin_address FROM btc_config WHERE idx=?', (idx,)) is None:
            db.query('INSERT INTO btc_config VALUES (?, ?)', (idx, address_num))
            await message.answer(f'Адрес <b>{address_num}</b> успешно добавлен в базу!', reply_markup=back_markup())

        else:
            address_num = db.fetchone('SELECT admin_address FROM btc_config WHERE idx=?', (idx,))[0]
            await message.answer(f'Адрес <b>{address_num}</b> уже есть в базе!')
        await state.finish()


@dp.message_handler(IsAdmin(), text=back_message)
async def btc_submit_cancel(message: Message):
    if message.text == back_message:
        await BTCConfigState.submit.set()
        await message.answer('Отменено!')
        await process_btc_config(message)


@dp.callback_query_handler(IsAdmin(), btc_setting_cb.filter(action='del_address'))
async def process_delete_address(query: CallbackQuery, callback_data: dict):
    idx = callback_data['id']
    db.query('DELETE FROM btc_config WHERE idx=?', (idx,))
    await query.answer('Удалено!')
    await query.message.delete()


# Настройка KUNA кошелька

@dp.message_handler(IsAdmin(), text='Настройка KUNA-кошелька')
async def process_kuna_config(message: Message):
    api_keys = db.fetchall('SELECT * FROM kuna_config')
    kuna_markup = ReplyKeyboardMarkup()
    kuna_markup.add('Заменить ключи KUNA', back_message)
    if len(api_keys) == 0:
        await message.answer('На данный момент ни один аккаунт KUNA не был добавлен в бот.', reply_markup=kuna_markup)
    elif len(api_keys) <= 2:
        api = api_keys[0]
        await message.answer(f'''Актуальная пара KUNA API KEYS:
PUBLIC KEY: <b>{api[0]}</b>
SECRET KEY: <b>{api[1]}</b>''', reply_markup=kuna_markup)


@dp.message_handler(IsAdmin(), text=back_message)
async def process_kuna_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!')
        await process_settings(message)


@dp.message_handler(IsAdmin(), text='Заменить ключи KUNA')
async def edit_kuna_keys(message: Message):
    await KunaConfigState.api_key.set()
    await message.answer('''Введите PUBLIC KEY аккаунта, который хотите подключить к боту.
Инструкция о том, что это и где взять тут: ссылка
Если желаете удалить актуальные ключи – пришлите сообщение с текстом "DELETE KUNA KEYS"''', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=KunaConfigState.api_key)
async def edit_kuna_keys_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_kuna_config(message)


@dp.message_handler(IsAdmin(), text='DELETE KUNA KEYS')
async def process_kuna_apikey_delete(message: Message):
    api_keys = db.fetchall('SELECT * FROM kuna_config')
    if len(api_keys) > 0:
        db.query('DELETE FROM kuna_config')
        await message.answer('Ключи были удалены.')
    else:
        await message.answer('Удалять нечего!')
    await process_settings(message)


@dp.message_handler(IsAdmin(), state=KunaConfigState.api_key)
async def process_kuna_apikey(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['api_key'] = message.text
    await message.answer('Теперь введите SECRET_KEY для подключения аккаунта KUNA.', reply_markup=back_markup())
    await KunaConfigState.next()


@dp.message_handler(IsAdmin(), text=back_message, state=KunaConfigState.api_secret)
async def process_kuna_apikey_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_kuna_config(message)


@dp.message_handler(IsAdmin(), state=KunaConfigState.api_secret)
async def process_kuna_api_secret(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['api_secret'] = message.text
        api_key = data['api_key']
    await message.answer(f'''Убедитесь, что все верно:
PUBLIC KEY: <b>{api_key}</b>
SECRET KEY: <b>{data['api_secret']}</b>''', reply_markup=submit_markup())
    await KunaConfigState.next()


@dp.message_handler(IsAdmin(), text=cancel_message, state=KunaConfigState.submit)
async def process_kuna_api_secret_cancel(message: Message, state: FSMContext):
    if message.text == cancel_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_settings(message)


@dp.message_handler(IsAdmin(), text=all_right_message, state=KunaConfigState.submit)
async def process_kuna_submit(message: Message, state: FSMContext):
    async with state.proxy() as data:
        api_key = data['api_key']
        api_secret = data['api_secret']
        api_keys = db.fetchall('SELECT * FROM kuna_config')
        if len(api_keys) == 0:
            db.query('INSERT INTO kuna_config VALUES (?, ?)', (api_key, api_secret))
        else:
            db.query('UPDATE kuna_config SET api_key=?, api_secret=?', (api_key,))
    await message.answer(f'''<b>PUBLIC KEY</b>: "{api_key}"
<b>SECRET KEY</b> "{api_secret}"
Ключи успешно добавлены в базу!''', reply_markup=back_markup())
    await state.finish()


@dp.message_handler(IsAdmin(), text=back_message)
async def process_kuna_submit_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!')
        await process_settings(message)

# НАСТРОЙКИ БОНУСОВ #


@dp.message_handler(IsAdmin(), text=bonus_settings)
async def bonus_set_process(message: Message):
    await SetBonusState.cid.set()
    await message.answer('Перешлите любое сообщение пользователя, которому нужно изменить бонусный баланс.', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=SetBonusState.cid)
async def bonus_set_process_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_settings(message)


@dp.message_handler(IsAdmin(), state=SetBonusState.cid)
async def edit_bonus_balance(message: Message, state: FSMContext):
    if message.forward_from is None:
        first_name = message.forward_sender_name
    else:
        first_name = message.forward_from.first_name

    if db.fetchone('SELECT * FROM users WHERE first_name=?', (first_name,)) is None:
        await message.answer('Этот пользователь не является юзером бота.')
        await bonus_set_process(message)
    else:
        user = db.fetchone('SELECT * FROM users WHERE first_name=?', (first_name,))
        async with state.proxy() as data:
            data['cid'] = user[0]
            data['username'] = user[1]
            data['balance'] = db.fetchone('SELECT bonus FROM referral WHERE username=?', (data['username'],))[0]
        await message.answer(f'''Убедитесь, что все правильно:
<b>User ID:</b> {data['cid']}
<b>Username:</b> @{data['username']}
<b>First Name:</b> {first_name}''', reply_markup=submit_markup())
        await SetBonusState.bonus_amount.set()


@dp.message_handler(IsAdmin(), text=cancel_message, state=SetBonusState.bonus_amount)
async def edit_bonus_balance_cancel(message: Message, state: FSMContext):
    if message.text == cancel_message:
        await state.finish()
        await bonus_set_process(message)


@dp.message_handler(IsAdmin(), text=all_right_message, state=SetBonusState.bonus_amount)
async def set_amount_balance(message: Message):
    await SetBonusState.confirm.set()
    await message.answer('Введите кол-во бонусов к изменению, числом.', reply_markup=back_markup())


@dp.message_handler(IsAdmin(), text=back_message, state=SetBonusState.confirm)
async def set_amount_balance_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await state.finish()
        await bonus_set_process(message)


@dp.message_handler(IsAdmin(), lambda message: message.text.isdigit(), state=SetBonusState.confirm)
async def confirm_edit_balance(message: Message, state: FSMContext):
    bonus_markup = InlineKeyboardMarkup()
    async with state.proxy() as data:
        data['bonus_amount'] = message.text
        username = data['username']
        bonus_id = data['cid']
        balance = data['balance']

    bonus_markup.add(
            InlineKeyboardButton('Добавить бонусы', callback_data=bonus_setting_cb.new(id=bonus_id, action='add_bonus')))
    bonus_markup.add(
            InlineKeyboardButton('Списать бонусы', callback_data=bonus_setting_cb.new(id=bonus_id, action='del_bonus')))

    await message.answer(f'''<b>Username:</b> @{username}
Общий бонусный баланс пользователя: <b>{balance}$</b>''', reply_markup=bonus_markup)
    await state.reset_state(with_data=False)


@dp.callback_query_handler(IsAdmin(), bonus_setting_cb.filter(action=['add_bonus', 'del_bonus']))
async def set_bonus_amount(query: CallbackQuery, callback_data: dict, state: FSMContext):
    bonus_id = callback_data['id']
    action = callback_data['action']
    async with state.proxy() as data:
        balance = db.fetchone('SELECT bonus FROM referral WHERE cid=?', (bonus_id,))[0]
        username = data.get('username')
        bonus_amount = int(data['bonus_amount'])

    if action == 'add_bonus':
        balance += bonus_amount
        db.query('UPDATE referral SET bonus=? WHERE cid=? AND username=?', (balance, bonus_id, username))
        await query.message.answer(f'Бонусы успешно добавлены на бонусный счет @{username}')
        await bot.send_message(bonus_id, f'На ваш бонусный счёт зачислено <b>{bonus_amount}$</b>!')
        await query.message.delete()
        await process_settings(query.message)

    if action == 'del_bonus':
        balance -= bonus_amount
        db.query('UPDATE referral SET bonus=? WHERE cid=? AND username=?', (balance, bonus_id, username))
        await query.message.answer(f'Бонусы успешно списаны с бонусного счета @{username}')
        await bot.send_message(bonus_id, f'С вашего бонусного счёта списано <b>{bonus_amount}$</b>!')
        await query.message.delete()
        await process_settings(query.message)


# Бот в каналах


@dp.message_handler(IsAdmin(), text=chat_settings)
async def process_chat_settings(message: Message):
    chat_markup = ReplyKeyboardMarkup()
    chat_markup.add('Добавить канал', back_message)
    if db.fetchall('SELECT * FROM channels') is None or len(db.fetchall('SELECT * FROM channels')) < 1:
        await message.answer('Ни один канал еще не был подключен!', reply_markup=chat_markup)
    else:
        await message.answer('Список каналов:', reply_markup=chat_markup)
        channels = db.fetchall('SELECT * FROM channels')
        for channel in channels:
            channel_id = channel[0]
            channel_username = channel[1]
            channel_name = channel[2]
            channel_role = channel[3]

            chatlist_markup = InlineKeyboardMarkup()
            chatlist_markup.add(InlineKeyboardButton('Удалить канал', callback_data=channel_setting_cb.new(id=channel_id, action='delete_channel')))
            await message.answer(f'''Данные канала:
            
<b>ID канала:</b> {abs(int(channel_id))}
<b>Username:</b> @{channel_username}
<b>Название канала:</b> {channel_name.capitalize()}
<b>Роль:</b> {channel_role}''', reply_markup=chatlist_markup)


@dp.message_handler(IsAdmin(), text=back_message)
async def process_chat_settings_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!')
        await process_settings(message)


@dp.message_handler(IsAdmin(), text='Добавить канал')
async def process_add_channel(message: Message):
    await ChannelState.channel_id.set()
    await message.answer('''Перешлите любое сообщение из канала, который хотите подключить к боту.
Бот ОБЯЗАТЕЛЬНО должен быть администратором канала!''', reply_markup=submit_markup())


@dp.message_handler(IsAdmin(), text=cancel_message, state=ChannelState.channel_id)
async def process_add_channel_cancel(message: Message):
    if message.text == cancel_message:
        await message.answer('Отменено!')
        await process_settings(message)


@dp.message_handler(IsAdmin(), state=ChannelState.channel_id)
async def process_add_channel_id(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['channel_username'] = message.forward_from_chat.username
        data['channel_name'] = message.forward_from_chat.full_name
        data['channel_id'] = message.forward_from_chat.id
    channel_markup = ReplyKeyboardMarkup()
    channel_markup.add('Для отзывов', 'Для заказов')
    channel_markup.add(back_message)
    await message.answer('Выберите роль выбранного канала. Что бот будет туда отправлять?', reply_markup=channel_markup)
    await ChannelState.role.set()


@dp.message_handler(text=back_message, state=ChannelState.role)
async def process_add_channel_id_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_chat_settings(message)


@dp.message_handler(IsAdmin(), lambda message: message.text in ['Для отзывов', 'Для заказов'], state=ChannelState.role)
async def process_add_channel_role(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['channel_role'] = message.text
        channel_id = data['channel_id']
        channel_username = data['channel_username']
        channel_name = data['channel_name']
    await message.answer(f'''Убедитесь, что все правильно.
    
<b>ID канала:</b> {abs(int(channel_id))}
<b>Username:</b> @{channel_username}
<b>Название канала:</b> {channel_name.capitalize()}
<b>Роль:</b> {data['channel_role']}''', reply_markup=submit_markup())
    await ChannelState.submit.set()


@dp.message_handler(text=cancel_message, state=ChannelState.submit)
async def process_add_channel_role_cancel(message: Message, state: FSMContext):
    if message.text == cancel_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_chat_settings(message)


@dp.message_handler(IsAdmin(), text=all_right_message, state=ChannelState.submit)
async def process_add_channel_submit(message: Message, state: FSMContext):
    async with state.proxy() as data:
        channel_role = data['channel_role']
        channel_id = data['channel_id']
        channel_username = data['channel_username']
        channel_name = data['channel_name']
        if db.fetchone('SELECT channel_username FROM channels WHERE channel_id=?', (channel_id,)) is None:
            db.query('INSERT INTO channels VALUES (?, ?, ?, ?)', (channel_id, channel_username, channel_name, channel_role))
            await message.answer(f'Канал {channel_role.lower()} успешно добавлен в базу.')
            await state.finish()
            await process_settings(message)
        else:
            await message.answer('Канал уже добавлен в базу!')
            await process_settings(message)


@dp.callback_query_handler(IsAdmin(), channel_setting_cb.filter(action='delete_channel'))
async def process_delete_channel(query: CallbackQuery, callback_data: dict):
    channel_id = callback_data['id']
    db.query('DELETE FROM channels WHERE channel_id=?', (channel_id,))
    await query.answer('Удалено!')
    await query.message.delete()


@dp.message_handler(IsAdmin(), text=contact_settings)
async def contact_settings_process(message: Message):
    await message.answer('Это раздел контактов. Здесь вы можете добавить/удалить контакты в боте.', reply_markup=back_markup())
    if db.fetchone('SELECT * FROM contacts') is None:
        add_contact_markup = ReplyKeyboardMarkup()
        add_contact_markup.add('Добавить контакты', back_message)
        await message.answer('Контактов пока нет.', reply_markup=add_contact_markup)
    else:
        await message.answer('Список добавленных контактов:')
        contacts = db.fetchall('SELECT * FROM contacts')
        add_contact_markup = InlineKeyboardMarkup()
        for contact in contacts:
            cid = str(contact[0])
            username = contact[1]
            role = contact[2]
            add_contact_markup.add(InlineKeyboardButton(f'Удалить контакт', callback_data=contacts_setting_cb.new(cid=cid, action='del_contact')))
            await message.answer(f'{role} @{username}', reply_markup=add_contact_markup)


@dp.message_handler(text=back_message)
async def process_contacts_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!')
        await process_settings(message)


@dp.message_handler(IsAdmin(), text='Добавить контакты')
async def add_contacts_process(message: Message):
    await message.answer('''Перешлите любое сообщение того, кого хотите добавить в контакты, в чат с ботом.
Он ОБЯЗАТЕЛЬНО должен быть юзером бота!''', reply_markup=back_markup())
    await ContactState.info.set()


@dp.message_handler(text=back_message, state=ContactState.info)
async def process_add_contacts_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await contact_settings_process(message)


@dp.message_handler(IsAdmin(), state=ContactState.info)
async def contact_info_process(message: Message, state: FSMContext):
    if message.forward_from is None:
        first_name = message.forward_sender_name
    else:
        first_name = message.forward_from.first_name

    async with state.proxy() as data:
        user = db.fetchone('SELECT * FROM users WHERE first_name=?', (first_name,))
        data['info'] = [str(user[0]), user[1]]
    contact_markup = ReplyKeyboardMarkup()
    contact_markup.add('Оператор', 'Админ')
    contact_markup.add(back_message)
    await message.answer('Выберите, кем является контакт для связи', reply_markup=contact_markup)
    await ContactState.role.set()


@dp.message_handler(text=back_message, state=ContactState.role)
async def process_add_contact_role_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!')
        await ContactState.info.set()


@dp.message_handler(IsAdmin(), lambda message: message.text in ['Оператор', 'Админ'], state=ContactState.role)
async def contact_role_process(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['role'] = message.text
        cid = data['info'][0]
        username = data['info'][1]
    await message.answer(f'''Убедитесь, что все правильно.
<b>User ID:</b> {cid}
<b>Username:</b> {username}
<b>Роль:</b> {data["role"]}''', reply_markup=submit_markup())
    await ContactState.submit.set()


@dp.message_handler(text=cancel_message, state=ContactState.submit)
async def process_submit_contacts_back(message: Message):
    if message.text == back_message:
        await message.answer('Отменено!')
        await ContactState.role.set()


@dp.message_handler(IsAdmin(), text=all_right_message, state=ContactState.submit)
async def contact_submit_process(message: Message, state: FSMContext):
    async with state.proxy() as data:
        cid = data['info'][0]
        username = data['info'][1]
        role = data['role']
    if db.fetchone('SELECT username FROM contacts WHERE cid=?', (cid,)) is None and db.fetchone('SELECT username FROM contacts WHERE role=?', (role,)) is None:
        db.query('INSERT INTO contacts VALUES (?, ?, ?)', (cid, username, role))
        await message.answer('Контакты были успешно добавлены в бота!')
        await state.finish()
        await contact_settings_process(message)
    else:
        await message.answer('Такой пользователь уже есть в базе или эта роль занята.')


@dp.callback_query_handler(IsAdmin(), contacts_setting_cb.filter(action='del_contact'))
async def callback_handler_add_contacts(query: CallbackQuery, callback_data: dict):
    cid = callback_data['cid']
    db.query('DELETE FROM contacts WHERE cid=?', (cid,))
    await query.message.delete()
    await query.message.answer('Удалено!')
    await contact_settings_process(query.message)
