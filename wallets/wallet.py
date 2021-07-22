from bit.wallet import PrivateKey as Key
from bit.network import NetworkAPI as net, satoshi_to_currency
from states.wallet_state import BTCState
from bit import *
from loader import db, dp
from hashlib import md5

addresses = []


@dp.message_handler(state=BTCState.submit)
async def wallet_key():
    k = Key().to_wif()
    key = Key(k)
    wallet_balance = key.balance_as('btc')
    address = key.address
    key = key.to_bytes()
    idx = md5(''.join([str(key), str(wallet_balance), str(address)]).encode('utf-8')).hexdigest()
    db.query('INSERT INTO wallet VALUES (?, ?, ?, ?)', (idx, key, address, int(wallet_balance)))
    global addresses
    addresses.append(idx)
    return address


async def get_address():
    global addresses
    idx = addresses[0]
    address = db.fetchone('SELECT address_num FROM wallet WHERE id = ?', (idx,))
    return address


async def get_address_balance(address):
    address_balance = net.get_balance(address)
    db.query('UPDATE wallet SET balance = ? WHERE address_num = ?', (int(address_balance), str(address)))
    return address_balance


async def send_btc():
    idx = addresses[0]
    k = db.fetchone('SELECT wallet_id FROM wallet WHERE id = ?', (idx,))[0]
    key = Key.from_bytes(k)
    if db.fetchone('SELECT * FROM btc_config') is None:
        return False
    else:
        admin_address = db.fetchone('SELECT * FROM btc_config')[0]
    key.send([], leftover=admin_address[1])
    addresses.clear()


async def check_payment(btc_total):
    address = await wallet_key()
    balance = await get_address_balance(address)
    btc_balance = float(satoshi_to_currency(balance, 'btc'))
    if float(btc_balance) >= float(btc_total):
        await send_btc()
        return True
    elif float(btc_balance) == 0 or float(btc_balance) < float(btc_total):
        return False
