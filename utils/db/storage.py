from data.config import ADMIN_ID, ADMIN_USERNAME, ADMIN_FIRSTNAME
import sqlite3 as lite


class DatabaseManager(object):

    def __init__(self, path):
        self.conn = lite.connect(path)
        self.conn.execute('pragma foreign_keys = on')
        self.conn.commit()
        self.cur = self.conn.cursor()

    def create_tables(self):
        self.query('CREATE TABLE IF NOT EXISTS contacts (cid int UNIQUE, username text UNIQUE, role text UNIQUE)')
        self.query('CREATE TABLE IF NOT EXISTS users (cid int UNIQUE, username text UNIQUE, first_name text, referred text)')
        self.query('CREATE TABLE IF NOT EXISTS referral (cid int UNIQUE, username text UNIQUE, ref_users text, ref_buyers text, bonus real)')
        self.query('CREATE TABLE IF NOT EXISTS buyers (cid int UNIQUE, username text UNIQUE, first_name text)')
        self.query('CREATE TABLE IF NOT EXISTS admins (cid int UNIQUE, username text UNIQUE, first_name text, role text)')
        self.query('CREATE TABLE IF NOT EXISTS products (idx text, title text, body text, photo blob, price real, amount int, tag text)')
        self.query('CREATE TABLE IF NOT EXISTS orders (cid int, username text, order_id text, address text, ttn int, products text, post_kind TEXT DEFAULT "null")')
        self.query('CREATE TABLE IF NOT EXISTS wallet (id int, wallet_id blob, address_num blob, balance real)')
        self.query('CREATE TABLE IF NOT EXISTS btc_config (idx text, admin_address text)')
        self.query('CREATE TABLE IF NOT EXISTS kuna_config (api_key text, api_secret text)')
        self.query('CREATE TABLE IF NOT EXISTS kuna_codes (id INTEGER PRIMARY KEY, cid int, code text, status numeric DEFAULT 0)')
        self.query('CREATE TABLE IF NOT EXISTS cart (cid int, idx text, quantity int, payment_status TEXT DEFAULT "null")')
        self.query('CREATE TABLE IF NOT EXISTS categories (idx text, title text)')
        self.query('CREATE TABLE IF NOT EXISTS questions (cid int, question text)')
        self.query('CREATE TABLE IF NOT EXISTS reviews (idx text, cid int, user text, category text, product_name text, review text, photo blob)')
        self.query('CREATE TABLE IF NOT EXISTS channels (channel_id int UNIQUE, channel_username text, channel_name text, role text)')
        self.query('CREATE TABLE IF NOT EXISTS work (idx text, cid int UNIQUE, username text, form text)')
        self.query('INSERT OR REPLACE INTO admins VALUES (?, ?, ?, ?)', (ADMIN_ID, ADMIN_USERNAME, ADMIN_FIRSTNAME, 'Админ'))

    def query(self, arg, values=None):
        if values is None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        self.conn.commit()

    def fetchone(self, arg, values=None):
        if values is None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        return self.cur.fetchone()

    def fetchall(self, arg, values=None):
        if values is None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        return self.cur.fetchall()

    def __del__(self):
        self.conn.close()



'''

products: idx text, title text, body text, photo blob, price int, tag text

orders: cid int, usr_name text, usr_address text, products text

cart: cid int, idx text, quantity int ==> product_idx

categories: idx text, title text

wallet: cid int, balance real

questions: cid int, question text

'''
