import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

# ============================================
# ПАРАМЕТРЫ ПО УМОЛЧАНИЮ
# ============================================
n_customers = 1000
n_transactions = 100000
start_date = '2020-01-01'
end_date = '2026-12-31'

# ============================================
# ЧТЕНИЕ ПАРАМЕТРОВ ИЗ КОМАНДНОЙ СТРОКИ
# ============================================
if len(sys.argv) > 1:
    n_customers = int(sys.argv[1])
if len(sys.argv) > 2:
    n_transactions = int(sys.argv[2])
if len(sys.argv) > 3:
    start_date = sys.argv[3]
if len(sys.argv) > 4:
    end_date = sys.argv[4]

np.random.seed(42)

# Подключение к БД
conn = sqlite3.connect('test_db.db')

# 1. Клиенты
reg_dates = pd.date_range(start=start_date, end=end_date, freq='D')
customers = pd.DataFrame({
    'customer_id': range(1, n_customers + 1),
    'registration_date': np.random.choice(reg_dates, n_customers),
    'region': np.random.choice(['Москва', 'СПб', 'Регионы', 'Другие'], n_customers),
    'segment': np.random.choice(['VIP', 'Средний', 'Массовый'], n_customers, p=[0.1, 0.3, 0.6])
})

# 2. Транзакции
transactions_data = []
for i in range(n_transactions):
    customer_id = np.random.randint(1, n_customers + 1)
    days_offset = np.random.randint(0, 730)
    trans_date = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=days_offset)
    
    segment = customers.loc[customer_id - 1, 'segment']
    if segment == 'VIP':
        amount = np.random.gamma(5, 2000)
    elif segment == 'Средний':
        amount = np.random.gamma(3, 500)
    else:
        amount = np.random.gamma(2, 150)
    
    transactions_data.append({
        'transaction_id': i + 1,
        'customer_id': customer_id,
        'transaction_date': trans_date.strftime('%Y-%m-%d'),
        'amount': round(amount, 2),
        'payment_method': np.random.choice(['Карта', 'Наличные', 'Перевод'], p=[0.5, 0.2, 0.3])
    })
transactions = pd.DataFrame(transactions_data)

# 3. Денежный поток
dates = pd.date_range(start=start_date, end=end_date, freq='D')
cashflow = pd.DataFrame({
    'date': dates.strftime('%Y-%m-%d'),
    'total_revenue': np.random.normal(100000, 15000, len(dates)) + 
                     np.sin(np.arange(len(dates)) * 2 * np.pi / 30) * 20000
})
trend = np.linspace(0, 0.3, len(dates))
cashflow['total_revenue'] = cashflow['total_revenue'] * (1 + trend)
cashflow['total_revenue'] = np.maximum(cashflow['total_revenue'], 50000)
cashflow['total_revenue'] = cashflow['total_revenue'].round(2)

# 4. Сохранение в БД
customers.to_sql('customers', conn, if_exists='replace', index=False)
transactions.to_sql('transactions', conn, if_exists='replace', index=False)
cashflow.to_sql('cashflow', conn, if_exists='replace', index=False)

conn.close()

print("[OK] Тестовая БД создана в корневой папке: test_db.db")
print(f"   Клиентов: {len(customers)}")
print(f"   Транзакций: {len(transactions)}")
print(f"   Денежный поток: {len(cashflow)} записей")
