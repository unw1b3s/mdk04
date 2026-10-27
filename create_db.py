"""Создание схемы без удаления существующих данных."""
import argparse
import logging
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def create_db(path):
    with closing(sqlite3.connect(str(path))) as conn, conn:
        conn.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        logging.info('Созданы/проверены таблицы: %s', ', '.join(tables))
    return tables


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, default=ROOT / 'shop.db')
    args = parser.parse_args()
    try:
        create_db(args.db)
    except (sqlite3.Error, OSError) as error:
        logging.error('Не удалось создать БД: %s', error)
        raise SystemExit(1)
