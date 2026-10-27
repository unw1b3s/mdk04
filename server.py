"""Локальный учебный сервер. Вход по логину без пароля — по заданию."""
import argparse
import json
import logging
import mimetypes
import secrets
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from create_db import ROOT


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def positive_int(value):
    if type(value) is not int or value <= 0:
        raise ApiError(400, 'Ожидается положительное целое число.')
    return value


class Handler(BaseHTTPRequestHandler):
    def send_data(self, status, data, content_type='application/json; charset=utf-8', cookie=None):
        if content_type.startswith('application/json'):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def connect(self):
        conn = sqlite3.connect(str(self.server.db))
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def user(self, conn):
        cookies = SimpleCookie()
        cookies.load(self.headers.get('Cookie', ''))
        token = cookies.get('session')
        user_id = self.server.sessions.get(token.value if token else '')
        user = conn.execute('SELECT * FROM Users WHERE id=?', (user_id,)).fetchone()
        if not user:
            raise ApiError(401, 'Сначала войдите по логину.')
        return user

    def staff(self, conn, admin=False):
        user = self.user(conn)
        roles = ('Администратор',) if admin else ('Менеджер', 'Администратор')
        if user['role'] not in roles:
            raise ApiError(403, 'Недостаточно прав.')
        return user

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, post):
        try:
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            if post:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 1 or length > 16384:
                    raise ApiError(400, 'Недопустимый размер запроса.')
                if self.headers.get_content_type() != 'application/json':
                    raise ApiError(415, 'Нужен JSON.')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ApiError(400, 'Нужен объект JSON.')
            with closing(self.connect()) as conn, conn:
                if not post and url.path == '/api/login':
                    login = query.get('login', [''])[0].strip()
                    if not login:
                        raise ApiError(400, 'Введите логин.')
                    row = conn.execute('SELECT id, full_name, role FROM Users WHERE login=?', (login,)).fetchone()
                    if not row:
                        raise ApiError(404, 'Логин не найден.')
                    token = secrets.token_urlsafe(24)
                    self.server.sessions[token] = row['id']
                    self.send_data(200, dict(row), cookie='session=' + token + '; HttpOnly; SameSite=Strict; Path=/')
                elif post and url.path == '/api/logout':
                    cookies = SimpleCookie(self.headers.get('Cookie', ''))
                    token = cookies.get('session')
                    self.server.sessions.pop(token.value if token else '', None)
                    self.send_data(200, {'ok': True}, cookie='session=; Max-Age=0; Path=/')
                elif not post and url.path == '/api/products':
                    rows = conn.execute('''SELECT p.*, c.name AS category, m.name AS manufacturer,
                        COALESCE(SUM(s.quantity), 0) AS quantity FROM Products p
                        JOIN Categories c ON c.id=p.category_id
                        JOIN Manufacturers m ON m.id=p.manufacturer_id
                        LEFT JOIN Stock s ON s.product_id=p.id GROUP BY p.id''').fetchall()
                    self.send_data(200, [dict(row) for row in rows])
                elif not post and url.path == '/api/orders':
                    self.staff(conn)
                    rows = conn.execute('''SELECT o.id, o.order_date, u.full_name FROM Orders o
                        JOIN Users u ON u.id=o.user_id ORDER BY o.id''').fetchall()
                    self.send_data(200, [dict(row) for row in rows])
                elif not post and url.path == '/api/order':
                    self.staff(conn)
                    order_id = positive_int(int(query.get('id', ['0'])[0]))
                    order = conn.execute('SELECT * FROM Orders WHERE id=?', (order_id,)).fetchone()
                    if not order:
                        raise ApiError(404, 'Заказ не найден.')
                    items = conn.execute('''SELECT i.*, p.name, s.value AS size,
                        i.quantity*i.unit_price AS total FROM OrderItems i
                        JOIN Products p ON p.id=i.product_id JOIN Sizes s ON s.id=i.size_id
                        WHERE i.order_id=? ORDER BY i.id''', (order_id,)).fetchall()
                    result = dict(order)
                    result['items'] = [dict(row) for row in items]
                    result['total'] = sum(row['total'] for row in items)
                    self.send_data(200, result)
                elif post and url.path == '/api/order/update':
                    self.staff(conn, admin=True)
                    self.update_order(conn, body)
                    conn.commit()
                    self.send_data(200, {'ok': True})
                elif url.path.startswith('/api/') or post:
                    raise ApiError(404, 'Адрес не найден.')
                else:
                    files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/favicon.ico': 'favicon.svg'}
                    name = files.get(url.path)
                    if not name:
                        raise ApiError(404, 'Файл не найден.')
                    path = ROOT / 'static' / name
                    mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
                    self.send_data(200, path.read_bytes(), mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
        except ApiError as error:
            self.send_data(error.status, {'error': error.message})
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_data(400, {'error': 'Проверьте формат данных.'})
        except (sqlite3.Error, OSError):
            logging.exception('Ошибка обработки запроса')
            self.send_data(500, {'error': 'Не удалось прочитать или сохранить данные.'})

    def update_order(self, conn, body):
        order_id = positive_int(body.get('id'))
        value = body.get('order_date')
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ApiError(400, 'Введите дату в формате ГГГГ-ММ-ДД.')
        deleted = body.get('deleted_item_ids', [])
        if not isinstance(deleted, list):
            raise ApiError(400, 'Нужен список удаляемых позиций.')
        for item_id in deleted:
            positive_int(item_id)
        if len(set(deleted)) != len(deleted):
            raise ApiError(400, 'Позиции не должны повторяться.')
        # Проверка и возврат остатков проходят в одной транзакции.
        conn.execute('BEGIN IMMEDIATE')
        if not conn.execute('SELECT id FROM Orders WHERE id=?', (order_id,)).fetchone():
            raise ApiError(404, 'Заказ не найден.')
        for item_id in deleted:
            item = conn.execute('SELECT * FROM OrderItems WHERE id=? AND order_id=?', (item_id, order_id)).fetchone()
            if not item:
                raise ApiError(409, 'Позиция уже удалена или принадлежит другому заказу. Откройте заказ заново.')
            conn.execute('UPDATE Stock SET quantity=quantity+? WHERE product_id=? AND size_id=?',
                         (item['quantity'], item['product_id'], item['size_id']))
            conn.execute('DELETE FROM OrderItems WHERE id=?', (item_id,))
        conn.execute('UPDATE Orders SET order_date=? WHERE id=?', (value, order_id))


def make_server(db, port=8000):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.db = db
    server.sessions = {}
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=str, default=str(ROOT / 'shop.db'))
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not Path(args.db).is_file():
        parser.exit(1, 'Сначала выполните python3 create_db.py\n')
    logging.basicConfig(level=logging.INFO)
    server = make_server(args.db, args.port)
    print('Продажа обуви: http://localhost:%s' % server.server_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
