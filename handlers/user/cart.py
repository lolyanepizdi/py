import json
from hashlib import md5
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.inline.products_from_cart import product_markup, product_cb
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import *
from aiogram.types.chat import ChatActions
from states import CheckoutState, NewPostState, KunaState, SpentBonusState
from loader import dp, db, bot
from filters import IsUser
from .menu import cart
from bit.network import currency_to_satoshi, satoshi_to_currency
from bit.network import get_fee
from wallets.wallet import wallet_key, get_address_balance, get_address, send_btc, check_payment
from handlers.user.menu import user_menu
from wallets.kuna_wallet import check_kuna_code, activate_code, check_payment_code

global total_price

pay_markup = ReplyKeyboardMarkup()
pay_markup.add('Проверить оплату')
pay_markup.add(back_message)


@dp.message_handler(IsUser(), text=cart)
async def process_cart(message: Message, state: FSMContext):
    cart_data = db.fetchall('SELECT * FROM cart WHERE cid=?', (message.chat.id,))

    if len(cart_data) == 0:
        await message.answer('Ваша корзина пуста.')
    else:
        await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
        async with state.proxy() as data:
            data['products'] = {}
        order_cost = 0

        for _, idx, count_in_cart, _, in cart_data:
            product = db.fetchone('SELECT * FROM products WHERE idx=?', (idx,))

            if product is None:
                db.query('DELETE FROM cart WHERE idx=?', (idx,))
            else:
                _, title, body, image, price, amount, _ = product
                order_cost += price

                async with state.proxy() as data:
                    data['products'][idx] = [title, price, count_in_cart, amount]

                markup = product_markup(idx, count_in_cart)
                text = f'<b>{title}</b>\n\n{body}\n\nЦена: {order_cost}$'

                await message.answer_photo(photo=image, caption=text, reply_markup=markup)

        if order_cost != 0:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add('📦 Оплатить заказ')
            markup.add('💎 Потратить бонусы')
            markup.add(back_message)

            await message.answer('Перейти к оплате?', reply_markup=markup)


@dp.message_handler(IsUser(), text=back_message)
async def cart_back(message: Message):
    if message.text == back_message:
        await user_menu(message)


@dp.message_handler(IsUser(), text='📦 Оплатить заказ')
async def pay_order_process(message: Message):

    payment_markup = ReplyKeyboardMarkup()
    payment_markup.add('🌐 Bitcoin', '📩 KUNA Code')
    payment_markup.add(back_message)
    await message.answer('Выберите способ оплаты.', reply_markup=payment_markup)
    await CheckoutState.payment_status.set()


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.payment_status)
async def payment_pick_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await state.finish()
        await process_cart(message, state)


@dp.message_handler(IsUser(), text='💎 Потратить бонусы')
async def use_bonus_process(message: Message, state: FSMContext):
    bonus_markup = ReplyKeyboardMarkup()
    bonus_markup.add('Использовать все бонусы')
    bonus_markup.add(back_message)

    cid = message.from_user.id
    if db.fetchone('SELECT bonus FROM referral WHERE cid=?', (cid,)) is None:
        await message.answer('Произошла ошибка!')
        await process_cart(message, state)
    else:
        async with state.proxy() as data:
            data['total_price'] = {}

        bonus = db.fetchone('SELECT bonus FROM referral WHERE cid=?', (cid,))[0]

        if bonus < 10:
            await message.answer(f'''На вашем счету недостаточно бонусов для использования!
Всего бонусов накоплено: <b>{round(bonus, 2)}$</b>
Минимальное кол-во бонусов для использования: <b>10$</b>''', reply_markup=back_markup())
        else:
            await message.answer(f'''Всего бонусов накоплено: <b>{round(bonus, 2)}$</b>
''', reply_markup=bonus_markup)

            await SpentBonusState.total_cost.set()


@dp.message_handler(IsUser(), text=back_message, state=SpentBonusState.total_cost)
async def bonus_back_menu(message: Message, state: FSMContext):
    if message.text == back_message:
        await state.finish()
        await use_bonus_process(message, state)


@dp.message_handler(IsUser(), text='Использовать все бонусы', state=SpentBonusState.total_cost)
async def use_all_bonus_process(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if 'products' in data.keys():
            cid = message.from_user.id
            answer = ''
            total_price = 0

            for title, price, count_in_cart, _ in data['products'].values():
                tp = count_in_cart * price
                answer += f'<b>{title}</b> * {count_in_cart} шт. = <b>{tp}$</b>'
                total_price += tp
                bonus = db.fetchone('SELECT bonus FROM referral WHERE cid=?', (cid,))[0]

                if bonus >= total_price:
                    total_bonus_cost = total_price - 30
                    total_cost = 30
                    current_bonus = bonus - total_bonus_cost
                else:
                    if bonus <= 30:
                        total_cost = total_price - bonus
                        current_bonus = 0
                    else:
                        total_bonus_cost = total_price - 30
                        if bonus >= total_bonus_cost:
                            total_cost = 30
                            current_bonus = bonus - total_bonus_cost
                        else:
                            total_cost = (total_bonus_cost - bonus) + 30

                if 'total_price' in data.keys():
                    data['total_price'][cid] = [total_price, bonus, answer, current_bonus, total_cost, total_bonus_cost]

            if total_price < 30:
                await message.answer('🚫 Сумма для заказа меньше минимальной!', reply_markup=back_markup())

            if (total_price - int(bonus)) < 30:
                await message.answer(f'''Вы не можете оплатить бонусами свыше минимального заказа (<b>30$</b>)!
Всего бонусов накоплено: <b>{round(bonus, 2)}$</b>
Доступно для оплаты бонусами: <b>{total_price - 30}$</b>''', reply_markup=submit_markup())
            await SpentBonusState.bonus.set()


@dp.message_handler(IsUser(), text=cancel_message, state=SpentBonusState.bonus)
async def use_all_bonus_invalid(message: Message, state: FSMContext):
    await SpentBonusState.total_cost.set()
    await use_bonus_process(message, state)


@dp.message_handler(IsUser(), text=all_right_message, state=SpentBonusState.bonus)
async def use_all_bonus_confirm(message: Message, state: FSMContext):
    cid = message.from_user.id
    async with state.proxy() as data:
        for total_price, bonus, answer, current_bonus, total_cost, total_bonus_cost in data['total_price'].values():
            answer += f'Со скидкой <b>{total_bonus_cost - bonus}$</b>, всего к оплате: <b>{total_cost}$</b>'
            db.query('UPDATE referral SET bonus=? WHERE cid=?', (current_bonus, cid))

            await message.answer('Бонусы успешно списаны!')
            await pay_order_process(message)


@dp.callback_query_handler(IsUser(), product_cb.filter(action='count'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='increase'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='decrease'))
async def product_callback_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):
    idx = callback_data['id']
    action = callback_data['action']

    if 'count' == action:
        async with state.proxy() as data:

            if 'products' not in data.keys():
                await process_cart(query.message, state)

            else:
                await query.answer('Количество - ' + str(data['products'][idx][2]))

    else:
        async with state.proxy() as data:

            if 'products' not in data.keys():
                await process_cart(query.message, state)

            elif data['products'][idx][3] <= data['products'][idx][2]:
                data['products'][idx][2] += 0 if 'increase' == action else -1
                count_in_cart = data['products'][idx][2]

                await query.answer('Товара больше нет в наличии!')

            else:
                data['products'][idx][2] += 1 if 'increase' == action else -1
                count_in_cart = data['products'][idx][2]

                if count_in_cart == 0:
                    db.query('''DELETE FROM cart  WHERE cid = ? AND idx = ?''', (query.message.chat.id, idx))

                    await query.message.delete()
                    await cart_back(query.message)

                else:
                    db.query('''UPDATE cart SET quantity = ? WHERE cid = ? AND idx = ?''',
                             (count_in_cart, query.message.chat.id, idx))
                    await query.message.edit_reply_markup(product_markup(idx, count_in_cart))


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.payment_status)
async def payment_pick_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await state.finish()
        await process_cart(message, state)


# BITCOIN СПОСОБ ОПЛАТЫ #


@dp.message_handler(IsUser(), text='🌐 Bitcoin', state=CheckoutState.payment_status)
async def btc_payment(message: Message, state: FSMContext):
    async with state.proxy() as data:
        fee = get_fee(fast=False)
        btc_fee = satoshi_to_currency(fee, 'btc')
        address = await wallet_key()
        cid = message.chat.id
        if data.get('total_price') is None:
            if 'products' in data.keys():
                answer = ''
                total_price = 0

                for title, price, count_in_cart, _ in data['products'].values():
                    tp = count_in_cart * price
                    answer += f'<b>{title}</b> * {count_in_cart} шт. = <b>{tp}$</b>'
                    total_price += tp

                total_cost = total_price
        else:
            total_cost = data['total_price'][cid][4]
            answer = data['total_price'][cid][2]

        data['address'] = address
        total_sat = currency_to_satoshi(total_cost, 'usd')
        btc_price = satoshi_to_currency(total_sat, 'btc')
        data['btc_total'] = float(btc_price) - float(btc_fee)

        idx = db.fetchone("SELECT idx FROM cart WHERE cid=?", (cid,))[0]
        db.query("UPDATE cart SET payment_status=? WHERE idx=? AND cid=?", ('btc', idx, cid))

        bestchange_url = 'https://www.bestchange.ru/'

        await message.answer(f'''{answer}
    
Общая сумма заказа c учётом комиссии и бонусной скидки: <b>{total_cost}$</b> или <b>{round(data['btc_total'], 7)} BTC.</b>
Для оплаты вам требуется оплатить ровно такую же сумму на адрес: 
<b>{address}</b>

Список безопасных и выгодных обменников вы можете найти тут: <u>{bestchange_url}</u>''', reply_markup=pay_markup)
        await CheckoutState.check_cart.set()


# KUNA СПОСОБ ОПЛАТЫ #


@dp.message_handler(IsUser(), text='📩 KUNA Code', state=CheckoutState.payment_status)
async def kuna_payment(message: Message, state: FSMContext):
    cid = message.chat.id
    idx = db.fetchone("SELECT idx FROM cart WHERE cid=?", (cid,))[0]
    db.query("UPDATE cart SET payment_status=? WHERE idx=? AND cid=?", ('kuna', idx, cid))
    async with state.proxy() as data:
        if data.get('total_price') is None:
            if 'products' in data.keys():
                answer = ''
                total_price = 0

                for title, price, count_in_cart, _ in data['products'].values():
                    tp = count_in_cart * price
                    answer += f'<b>{title}</b> * {count_in_cart} шт. = <b>{tp}$</b>'
                    total_price += tp

                data['products'][idx].append(total_price)
                data['products'][idx].append(answer)
                total_cost = total_price
        else:
            total_cost = data['total_price'][cid][4]
            answer = data['total_price'][cid][2]

        await message.answer(f'''{answer}
Общая сумма заказа c учётом комиссии и бонусной скидки: <b>{total_cost}$</b>.
Для оплаты вам требуется создать KUNA Code ровно на такую же сумму.
После этого впишите код в строку для сообщений и нажмите на кнопку "Проверить оплату".''', reply_markup=pay_markup)
        await CheckoutState.check_cart.set()


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.check_cart)
async def process_check_kuna_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await pay_order_process(message)


@dp.message_handler(IsUser(), text='Проверить оплату', state=CheckoutState.check_cart)
async def process_checkout(message: Message, state: FSMContext):
    cid = message.chat.id
    idx = db.fetchone("SELECT idx FROM cart WHERE cid=?", (cid,))[0]
    payment_status = db.fetchone("SELECT payment_status FROM cart WHERE cid=? AND idx=?", (cid, idx))[0]
    if payment_status == 'paid':
        post_markup = ReplyKeyboardMarkup()
        post_markup.row('🇺🇦 УкрПочта', '🌀 Justin')
        post_markup.row('📮 Новая Почта')
        await message.answer('Выберите способ доставки!', reply_markup=post_markup)
        await CheckoutState.post_kind.set()

    if payment_status == 'btc':
        async with state.proxy() as data:
            btc_total = data['btc_total']
        payment = await check_payment(btc_total)

        if payment:
            payment_status = 'paid'
            db.query("UPDATE cart SET payment_status=? WHERE cid=? AND idx=?", (payment_status, cid, idx))
            post_markup = ReplyKeyboardMarkup()
            post_markup.row('🇺🇦 УкрПочта', '🌀 Justin')
            post_markup.row('📮 Новая Почта')
            await message.answer('✅ Оплата прошла успешно. Выберите способ доставки!', reply_markup=post_markup)
            await CheckoutState.post_kind.set()
        else:
            await message.answer('❌ Оплата еще не поступала на счёт или она меньше, чем сумма заказа.',
                                 reply_markup=pay_markup)
    if payment_status == 'kuna':
        await message.answer('Введите KUNA-код.')
        await KunaState.code.set()


@dp.message_handler(IsUser(), text=back_message, state=KunaState.code)
async def process_check_pay_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await pay_order_process(message)


@dp.message_handler(IsUser(), state=KunaState.code)
async def check_kuna_proccess(message: Message, state: FSMContext):
    code = message.text
    cid = message.chat.id
    idx = db.fetchone("SELECT idx FROM cart WHERE cid=?", (cid,))[0]
    async with state.proxy() as data:
        if 'total_cost' in data.keys():
            total_cost = data['total_cost'][cid][4]
            answer = data['total_cost'][cid][2]

        else:
            total_cost = data['products'][idx][4]
            answer = data['products'][idx][5]

    payment = check_payment_code(total_cost, code, cid)
    if payment is True:
        payment_status = 'paid'
        db.query("UPDATE cart SET payment_status=? WHERE cid=? AND idx=?", (payment_status, cid, idx))
        post_markup = ReplyKeyboardMarkup()
        post_markup.row('🇺🇦 УкрПочта', '🌀 Justin')
        post_markup.row('📮 Новая Почта')
        await message.answer('✅ Оплата прошла успешно. Выберите способ доставки!', reply_markup=post_markup)
        await CheckoutState.post_kind.set()
    if payment == 404:
        await message.answer('❌ Такой KUNA Code не был найден. Повторите попытку.', reply_markup=back_markup())
    if payment is False:
        await message.answer('❌ Этот KUNA Code не подходит! Повторите попытку.', reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.post_kind)
async def process_kuna_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await pay_order_process(message)


@dp.message_handler(IsUser(), text='🇺🇦 УкрПочта', state=CheckoutState.post_kind)
async def process_ukrpost_delivery(message: Message, state: FSMContext):
    post_kind = 'ukrpost'
    async with state.proxy() as data:
        data['post_kind'] = post_kind
    await CheckoutState.address.set()
    ukrpost_markup = ReplyKeyboardMarkup()
    ukrpost_markup.row(back_message)
    await message.answer('''Укажите данные для отправки одним сообщением в таком формате:
🔸 Номер телефона получателя
🔸 ФИО
🔸 Город, номер/индекс отделения Укрпочты''', reply_markup=ukrpost_markup)


@dp.message_handler(IsUser(), text='🌀 Justin', state=CheckoutState.post_kind)
async def process_justin_delivery(message: Message, state: FSMContext):
    post_kind = 'justin'
    async with state.proxy() as data:
        data['post_kind'] = post_kind
    await CheckoutState.address.set()

    justin_markup = ReplyKeyboardMarkup()
    justin_markup.row(back_message)
    await message.answer('''Укажите данные для отправки одним сообщением в таком формате:
🔸 Номер телефона получателя
🔸 ФИО
🔸 Город, номер отделения Justin''', reply_markup=justin_markup)


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.address)
async def process_check_cart_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await process_checkout(message, state)


@dp.message_handler(IsUser(), text='📮 Новая Почта', state=CheckoutState.post_kind)
async def newpost_delivery(message: Message, state: FSMContext):
    newpost_markup = ReplyKeyboardMarkup()
    newpost_markup.row(back_message, 'Продолжить с НП')
    await message.answer('''Мы настоятельно не рекомендуем пользоваться
услугами Новой почты, для Вашей же безопасности. Делая отправку через Новую Почту, 
мы не несём ответственность за любые происшествия которые могут возникнуть!''', reply_markup=newpost_markup)
    await NewPostState.submit.set()


@dp.message_handler(IsUser(), text='Продолжить с НП', state=NewPostState.submit)
async def process_newpost_delivery(message: Message, state: FSMContext):
    post_kind = 'newpost'
    async with state.proxy() as data:
        data['post_kind'] = post_kind
    await CheckoutState.address.set()

    new_post_markup = ReplyKeyboardMarkup()
    new_post_markup.add(back_message)
    await message.answer('''Укажите данные для отправки одним сообщением в таком формате:
    🔸 Номер телефона получателя
    🔸 ФИО
    🔸 Город, номер отделения НП''', reply_markup=new_post_markup)


@dp.message_handler(IsUser(), text=back_message, state=NewPostState.submit)
async def process_new_post_back(message: Message, state: FSMContext):
    if message.text == back_message:
        await process_checkout(message, state)


@dp.message_handler(IsUser(), state=CheckoutState.address)
async def process_info(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = message.text
        data['ttn'] = 0
        await confirm(message)
        await CheckoutState.confirm.set()


async def confirm(message):
    await message.answer('Убедитесь, что все правильно оформлено и подтвердите заказ.',
                         reply_markup=confirm_markup())


# @dp.message_handler(IsUser(), lambda message: message.text not in [confirm_message, back_message],
#                     state=CheckoutState.confirm)
# async def process_confirm_invalid(message: Message):
#     await message.reply('Такого варианта не было.')


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.confirm)
async def process_confirm_back(message: Message, state: FSMContext):
    await CheckoutState.address.set()

    async with state.proxy() as data:
        await message.answer('Изменить данные с <b>' + data['address'] + '</b>?',
                             reply_markup=back_markup())


@dp.message_handler(IsUser(), text=confirm_message, state=CheckoutState.confirm)
async def process_confirm(message: Message, state: FSMContext):
    async with state.proxy() as data:
        post_kind = data['post_kind']
        total_price = data['total_price']
        order_cb = CallbackData('order', 'id', 'action')
        cid = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name

        if 'products' not in data.keys():
            await process_cart(message, state)
        else:
            products = [f'{title.capitalize()} — {str(count_in_cart)}'
                        for title, _, count_in_cart, _, in data['products'].values()]
            order_id = md5(''.join([str(cid), data['address'], ' шт.'.join(products)]).encode('utf-8')).hexdigest()
            db.query('INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (cid, username, order_id, data['address'], data['ttn'], ''.join(products), post_kind))
            referred = db.fetchone('SELECT referred FROM users WHERE cid=?', (cid,))[0]
            referral = db.fetchone('SELECT * FROM referral WHERE username=?', (referred,))
            if referral is not None:
                ref_buyer = json.loads(referral[2])
                if cid not in ref_buyer:
                    ref_buyer.append(cid)
                db.query('UPDATE referral SET ref_buyers=? WHERE username=?', (json.dumps(ref_buyer), referral[0]))
                percent = (total_price / 100) * 3
                bonus = db.fetchone('SELECT bonus FROM referral WHERE username=?', (referral[0],))[0] + percent
                db.query('UPDATE referral SET bonus=? WHERE username=?', (bonus, referral[0]))

            buyer = db.fetchone('SELECT * FROM buyers WHERE cid=?', (cid,))
            if buyer is None:
                db.query('INSERT INTO buyers VALUES (?, ?, ?)', (cid, username, first_name))
            if post_kind == 'ukrpost':
                post_kind = '🇺🇦 Укрпочта'
            if post_kind == 'justin':
                post_kind = '🌀 Justin'
            if post_kind == 'newpost':
                post_kind = '📮 Новая Почта'

            db.query('DELETE FROM cart WHERE cid=?', (cid,))

            address = data['address'].split('\n')
            if len(products) > 1:
                product = ' шт.\n'.join(products)
            else:
                product = f'{"".join(products)} шт.'

                text = f'''Телефон: <b>{address[0]}</b>
<b>ФИО:</b> {address[1]}</b>
<b>Юзернэйм:</b> @{username}</b>
Город/почта:</b> {address[2]}</b>
Способ доставки:</b> {post_kind}</b>
Заказ:
<b>{product}</b>'''

            await message.answer(
                f'''Ок! Ваш заказ уже в пути 🚀
Телефон: <b>{address[0]}</b>
ФИО: <b>{address[1]}</b>
Город/почта: <b>{address[2]}</b>
Способ доставки: <b>{post_kind}</b>
Ваш заказ:
<b>{product}</b>''')

            answer_markup = InlineKeyboardMarkup()
            answer_markup.add(
                InlineKeyboardButton('Обновить ТТН', callback_data=order_cb.new(id=order_id, action='add_ttn')))
            answer_markup.add(
                InlineKeyboardButton('Удалить заказ', callback_data=order_cb.new(id=order_id, action='delete_order')))
            admins = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Админ',))[0]
            couriers = db.fetchall('SELECT cid FROM admins WHERE role=?', ('Курьер',))[0]
            if db.fetchone('SELECT channel_id FROM channels WHERE role=?', ('Для заказов',)) is None:
                for cid in admins and cid in couriers:
                    await bot.send_message(cid, text=text, reply_markup=answer_markup)
            else:
                channels = db.fetchall('SELECT channel_id FROM channels WHERE role=?', ('Для заказов',))[0]
                for channel in channels:
                    await bot.send_message(channel, text)
    await state.finish()
