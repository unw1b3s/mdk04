"""Интеграционные проверки на отдельной временной базе."""
from contextlib import closing
import http.cookiejar
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo_data import seed
from server import make_server


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.db'
        seed(self.db)
        self.server = make_server(self.db, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, raw=None):
        payload = json.dumps(data).encode() if data is not None else raw
        req = Request('http://127.0.0.1:%s%s' % (self.server.server_port, path),
                      data=payload, headers={'Content-Type': 'application/json'})
        try:
            response = self.client.open(req)
        except HTTPError as error:
            response = error
        with response:
            content = response.read()
            if 'application/json' in response.headers['Content-Type']:
                content = json.loads(content)
            return response.status, content

    def login(self, login):
        status, user = self.request('/api/login?login=' + login)
        self.assertEqual(status, 200)
        return user

    def sql(self, query):
        with closing(sqlite3.connect(str(self.db))) as conn, conn:
            return conn.execute(query).fetchall()

    def test_five_logins_and_unknown(self):
        for login, role in [('admin', 'Администратор'), ('manager', 'Менеджер'),
                            ('client1', 'Клиент'), ('client2', 'Клиент'), ('client3', 'Клиент')]:
            with self.subTest(login=login):
                self.assertEqual(self.login(login)['role'], role)
        self.assertEqual(self.request('/api/login?login=missing')[0], 404)
        self.assertEqual(self.request('/api/login?login=%27%20OR%201=1--')[0], 404)
        self.assertEqual(self.request('/api/login')[0], 400)

    def test_static_and_catalog(self):
        for path in ['/', '/app.js', '/style.css', '/favicon.ico']:
            self.assertEqual(self.request(path)[0], 200)
        self.assertEqual(len(self.request('/api/products')[1]), 4)
        for path in ['/schema.sql', '/shop.db', '/../server.py', '/missing']:
            self.assertEqual(self.request(path)[0], 404)

    def test_roles_and_logout(self):
        self.assertEqual(self.request('/api/orders')[0], 401)
        self.login('client1')
        self.assertEqual(self.request('/api/orders')[0], 403)
        self.login('manager')
        self.assertEqual(len(self.request('/api/orders')[1]), 2)
        self.assertEqual(self.request('/api/order?id=1')[1]['total'], 44000)
        self.assertEqual(self.request('/api/order/update', {'id': 1})[0], 403)
        self.request('/api/logout', {})
        self.assertEqual(self.request('/api/orders')[0], 401)

    def test_update_returns_stock_once(self):
        self.login('admin')
        before = self.sql('SELECT quantity FROM Stock WHERE product_id=1 AND size_id=1')[0][0]
        body = {'id': 1, 'order_date': '2026-10-20', 'deleted_item_ids': [1]}
        self.assertEqual(self.request('/api/order/update', body)[0], 200)
        self.assertEqual(self.sql('SELECT order_date FROM Orders WHERE id=1')[0][0], '2026-10-20')
        self.assertEqual(self.sql('SELECT quantity FROM Stock WHERE product_id=1 AND size_id=1')[0][0], before + 1)
        self.assertEqual(self.request('/api/order?id=1')[1]['total'], 32000)
        self.assertEqual(self.request('/api/order/update', body)[0], 409)
        self.assertEqual(self.sql('SELECT quantity FROM Stock WHERE product_id=1 AND size_id=1')[0][0], before + 1)

    def test_failed_update_rolls_back_every_change(self):
        self.login('admin')
        before = self.sql('SELECT * FROM Stock')
        original_date = self.sql('SELECT order_date FROM Orders WHERE id=1')
        body = {'id': 1, 'order_date': '2026-10-20', 'deleted_item_ids': [1, 3]}
        self.assertEqual(self.request('/api/order/update', body)[0], 409)
        self.assertEqual(self.sql('SELECT * FROM Stock'), before)
        self.assertEqual(self.sql('SELECT order_date FROM Orders WHERE id=1'), original_date)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM OrderItems')[0][0], 3)

    def test_invalid_requests(self):
        self.login('admin')
        for body in [[], {'id': '1'}, {'id': 1, 'order_date': '2026-02-30'},
                     {'id': True, 'order_date': '2026-10-20'},
                     {'id': 1, 'order_date': '2026-10-20', 'deleted_item_ids': [1, 1]},
                     {'id': 1, 'order_date': '2026-10-20', 'deleted_item_ids': ['1']}]:
            with self.subTest(body=body):
                self.assertEqual(self.request('/api/order/update', body)[0], 400)
        self.assertEqual(self.request('/api/order/update', raw=b'{broken')[0], 400)
        self.assertEqual(self.request('/api/order?id=999')[0], 404)
        self.assertEqual(self.request('/api/order?id=word')[0], 400)

    def test_database_constraints(self):
        statements = ["INSERT INTO Users VALUES (9,'admin','Имя','Клиент')",
                      'INSERT INTO Stock VALUES (999,1,1)',
                      'UPDATE Stock SET quantity=-1 WHERE product_id=1',
                      'UPDATE OrderItems SET quantity=0 WHERE id=1']
        with closing(sqlite3.connect(str(self.db))) as conn, conn:
            conn.execute('PRAGMA foreign_keys=ON')
            for sql in statements:
                with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(sql)
            conn.execute('DELETE FROM Orders WHERE id=1')
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM OrderItems WHERE order_id=1').fetchone()[0], 0)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
