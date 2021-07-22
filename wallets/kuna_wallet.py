import json
import requests
import time
import hmac
import hashlib
from loader import db


def activate_code(code):
    if db.fetchone('SELECT * FROM kuna_config') is None:
        return 'Error occurred'
    else:
        api_keys = db.fetchone('SELECT * FROM kuna_config')[0]
        public_key = api_keys[0]
        secret_key = api_keys[1]
    url = "https://api.kuna.io/v3/auth/kuna_codes/redeem"
    api_path = "/v3/auth/kuna_codes/redeem"

    payload = {"code": code}
    nonce = str(int(time.time()*1000.0))
    body = json.dumps(payload)
    msg = api_path+nonce+body

    kun_signature = hmac.new(secret_key.encode('ascii'), msg.encode('ascii'), hashlib.sha384).hexdigest()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        'kun-nonce': nonce,
        'kun-apikey': public_key,
        'kun-signature': kun_signature,
        }

    response = requests.request("PUT", url, json=payload, headers=headers)
    if response:
        return response.text
    else:
        return f"Error {response.status_code} - {response.reason} is occurred."


def check_kuna_code(code):
    res_dict = {}
    api_path = f'v3/kuna_codes/{code[:5]}/check'
    uri = 'https://api.kuna.io/' + api_path
    headers = {"Accept": "application/json"}
    response = requests.request("GET", uri, headers=headers)
    if response:
        response = response.json()
        res_dict['code'] = response['code']
        res_dict['recipient'] = response['recipient']
        res_dict['amount'] = response['amount']
        res_dict['status'] = response['status']
        res_dict['currency'] = response['currency']
        return res_dict
    else:
        return False


def check_payment_code(total_price, code, cid):
    code_status = check_kuna_code(code)
    bad_status = ['processing', 'unconfirmed', 'redeemed', 'onhold', 'canceled']
    if code_status is False:
        return 404
    elif code_status['amount'] < total_price or code_status['recipient'] != 'all' or code_status['status'] in bad_status or code_status['currency'] != 'usd':
        db.query("INSERT INTO kuna_codes(cid, code, status) VALUES (?, ?, ?)", (cid, code, 0))
        return False
    elif code_status['amount'] >= total_price:
        db.query("INSERT INTO kuna_codes(cid, code, status) VALUES (?, ?, ?)", (cid, code, 1))
        activate_code(code)
        return True
