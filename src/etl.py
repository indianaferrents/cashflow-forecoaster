import pandas as pd
import sqlite3
import sys
import os

# ============================================
# ПУТЬ К БАЗЕ ДАННЫХ (из командной строки или по умолчанию)
# ============================================
db_path = 'data/cashflow.db'
if len(sys.argv) > 1:
    db_path = sys.argv[1]

print(f"Используется БД: {db_path}")

def table_exists(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Если таблицы ещё нет, создание по схеме
    if not table_exists(conn, 'customers'):
        with open('sql/schema.sql', 'r', encoding='utf-8') as f:
            cursor.executescript(f.read())
        conn.commit()
        print("[OK] Схема БД создана")
    else:
        print("[OK] Схема БД уже существует")
    return conn

def load_data(conn):
    # Проверка, есть ли записи в таблице customers
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM customers")
    count = cursor.fetchone()[0]
    if count == 0:
        # Если пусто, загрузка из CSV
        try:
            customers = pd.read_csv('data/raw/customers.csv')
            transactions = pd.read_csv('data/raw/transactions.csv')
            cashflow = pd.read_csv('data/raw/cashflow.csv')
            customers.to_sql('customers', conn, if_exists='append', index=False)
            transactions.to_sql('transactions', conn, if_exists='append', index=False)
            cashflow.to_sql('cashflow', conn, if_exists='append', index=False)
            print("[OK] Данные загружены из CSV")
        except FileNotFoundError:
            print("[WARN] CSV-файлы не найдены, но БД уже содержит данные (пропускаем)")
    else:
        print("[OK] БД уже содержит данные, загрузка CSV пропущена")

def run_rfm_analysis(conn):
    # Проверка, есть ли таблица rfm_segments
    if not table_exists(conn, 'rfm_segments'):
        with open('sql/rfm_analysis.sql', 'r', encoding='utf-8') as f:
            query = f.read()
        rfm = pd.read_sql(query, conn)
        rfm.to_sql('rfm_segments', conn, if_exists='replace', index=False)
        print("[OK] RFM-сегменты рассчитаны")
    else:
        # Проверка, пуста ли таблица
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rfm_segments")
        count = cursor.fetchone()[0]
        if count == 0:
            with open('sql/rfm_analysis.sql', 'r', encoding='utf-8') as f:
                query = f.read()
            rfm = pd.read_sql(query, conn)
            rfm.to_sql('rfm_segments', conn, if_exists='replace', index=False)
            print("[OK] RFM-сегменты пересчитаны")
        else:
            print("[OK] RFM-сегменты уже существуют")
    # Возвращение первых 5 строк для проверки
    rfm = pd.read_sql('SELECT * FROM rfm_segments LIMIT 5', conn)
    return rfm

if __name__ == '__main__':
    conn = init_db()
    load_data(conn)
    rfm = run_rfm_analysis(conn)
    print(rfm)