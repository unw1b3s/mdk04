"""Только собственные демонстрационные данные, не импорт преподавателя."""
import argparse
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from create_db import ROOT, create_db


def seed(path):
    create_db(path)
    with closing(sqlite3.connect(str(path))) as conn, conn:
        conn.execute('PRAGMA foreign_keys = ON')
        if conn.execute('SELECT COUNT(*) FROM Products').fetchone()[0]:
            raise ValueError('База уже содержит товары. Используйте новую БД для демо.')
        conn.executemany('INSERT INTO Categories VALUES (?, ?)', [
            (1, 'Женская обувь'), (2, 'Мужская обувь')])
        conn.executemany('INSERT INTO Manufacturers VALUES (?, ?)', [
            (1, 'Учебная фабрика'), (2, 'Демо обувь')])
        conn.executemany('INSERT INTO Sizes VALUES (?, ?)', [(1, 37), (2, 38), (3, 42)])
        conn.executemany('INSERT INTO Users VALUES (?, ?, ?, ?)', [
            (1, 'admin', 'Иванова Анна Сергеевна', 'Администратор'),
            (2, 'manager', 'Петров Илья Андреевич', 'Менеджер'),
            (3, 'client1', 'Смирнова Ольга Ивановна', 'Клиент'),
            (4, 'client2', 'Соколов Артём Павлович', 'Клиент'),
            (5, 'client3', 'Морозова Ирина Олеговна', 'Клиент')])
        conn.executemany('INSERT INTO Products VALUES (?, ?, ?, ?, ?, ?)', [
            (1, 'Туфли Весна', 1, 1, 'Натуральная кожа', 12000),
            (2, 'Кеды Город', 1, 2, 'Текстиль', 4000),
            (3, 'Ботинки Осень', 2, 1, 'Натуральная кожа', 16000),
            (4, 'Кроссовки Старт', 2, 2, 'Текстиль', 7000)])
        conn.executemany('INSERT INTO Stock VALUES (?, ?, ?)', [
            (1, 1, 1), (1, 2, 1), (2, 1, 4), (2, 2, 5), (3, 3, 3), (4, 3, 0)])
        today = date.today()
        previous = today.replace(day=1) - timedelta(days=1)
        conn.executemany('INSERT INTO Orders VALUES (?, ?, ?)', [
            (1, previous.replace(day=10).isoformat(), 3), (2, today.isoformat(), 4)])
        conn.executemany('INSERT INTO OrderItems VALUES (?, ?, ?, ?, ?, ?)', [
            (1, 1, 1, 1, 1, 12000), (2, 1, 3, 3, 2, 16000),
            (3, 2, 2, 2, 1, 4000)])
    print('Демонстрационные данные: 5 пользователей, 4 товара, 2 заказа.')
    print('Остатки в Stock указаны уже после этих заказов.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, default=ROOT / 'shop.db')
    args = parser.parse_args()
    try:
        seed(args.db)
    except (ValueError, sqlite3.Error, OSError) as error:
        parser.exit(1, str(error) + '\n')
