import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from multiprocessing import Pool, cpu_count
import os

# ============================================
# ПАРАМЕТРЫ ПО УМОЛЧАНИЮ
# ============================================
n_customers = 1000
n_transactions = 10000
start_date = '2020-01-01'
end_date = '2025-12-31'

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

print("--- Параметры генерации ---")
print(f"Клиентов: {n_customers}")
print(f"Транзакций: {n_transactions}")
print(f"Период: {start_date} - {end_date}")

np.random.seed(42)

# ============================================
# ГЕНЕРАЦИЯ КЛИЕНТОВ
# ============================================
dates = pd.date_range(start=start_date, end=end_date, freq='D')

customers = pd.DataFrame({
    'customer_id': range(1, n_customers + 1),
    'registration_date': np.random.choice(dates, n_customers),
    'region': np.random.choice(['Москва', 'СПб', 'Регионы', 'Другие'], n_customers),
    'segment': np.random.choice(['VIP', 'Средний', 'Массовый'], n_customers, p=[0.1, 0.3, 0.6])
})

# Преобразование в список словарей для передачи в процессы
customers_list = customers.to_dict('records')
end_date_dt = pd.to_datetime(end_date)

# ============================================
# ПАРАЛЛЕЛЬНАЯ ГЕНЕРАЦИЯ ТРАНЗАКЦИЙ
# ============================================

# Глобальные переменные для процессов
_global_customers = None
_global_end_date = None

def init_process(customers_data, end_date_val):
    global _global_customers, _global_end_date
    _global_customers = customers_data
    _global_end_date = end_date_val

def generate_transaction(transaction_id):
    # Выбор случайного клиента
    customer = np.random.choice(_global_customers)
    customer_id = customer['customer_id']
    reg_date = customer['registration_date']
    
    # Генерация даты транзакции (от регистрации до end_date)
    max_days = (_global_end_date - reg_date).days
    if max_days < 0:
        # Если регистрация позже end_date (такое маловероятно, вроде, на всякий случай оставлю)
        trans_date = reg_date
    else:
        delta_days = np.random.randint(0, max_days + 1)
        trans_date = reg_date + timedelta(days=delta_days)
    
    # Зависимость суммы от сегмента
    segment = customer['segment']
    if segment == 'VIP':
        amount = np.random.gamma(5, 2000)
    elif segment == 'Средний':
        amount = np.random.gamma(3, 500)
    else:
        amount = np.random.gamma(2, 150)
    
    payment_method = np.random.choice(['Карта', 'Наличные', 'Перевод'], p=[0.5, 0.2, 0.3])
    
    return {
        'transaction_id': transaction_id + 1,
        'customer_id': customer_id,
        'transaction_date': trans_date,
        'amount': round(amount, 2),
        'payment_method': payment_method
    }

if __name__ == '__main__':
    # Определение количества процессов (используем все ядра, кроме одного)
    num_processes = max(1, cpu_count() - 1)
    print(f"Используется {num_processes} процессов для генерации транзакций...")
    
    with Pool(processes=num_processes,
              initializer=init_process,
              initargs=(customers_list, end_date_dt)) as pool:
        # Генерация транзакций параллельно
        # Использование imap для прогресса (опционально)
        results = pool.map(generate_transaction, range(n_transactions))
    
    transactions_df = pd.DataFrame(results)
    print(f"Сгенерировано {len(transactions_df)} транзакций.")

    # ============================================
    # ГЕНЕРАЦИЯ ДЕНЕЖНОГО ПОТОКА
    # ============================================
    cashflow = pd.DataFrame({
        'date': dates,
        'total_revenue': np.random.normal(100000, 15000, len(dates)) + 
                         np.sin(np.arange(len(dates)) * 2 * np.pi / 30) * 20000
    })
    # Добавление трендов
    trend = np.linspace(0, 0.3, len(dates))
    cashflow['total_revenue'] = cashflow['total_revenue'] * (1 + trend)
    cashflow['total_revenue'] = np.maximum(cashflow['total_revenue'], 50000)

    # ============================================
    # СОХРАНЕНИЕ
    # ============================================
    # Создание папки, если их нет
    os.makedirs('data/raw', exist_ok=True)
    
    customers.to_csv('data/raw/customers.csv', index=False)
    transactions_df.to_csv('data/raw/transactions.csv', index=False)
    cashflow.to_csv('data/raw/cashflow.csv', index=False)

    print("[OK] Данные сгенерированы и сохранены в data/raw/")