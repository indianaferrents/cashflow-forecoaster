import pandas as pd
import sqlite3
import numpy as np
import sys

# ============================================
# ПУТЬ К БАЗЕ ДАННЫХ (из командной строки или по умолчанию)
# ============================================
db_path = 'data/cashflow.db'
if len(sys.argv) > 1:
    db_path = sys.argv[1]

print(f"Используется БД: {db_path}")

def aggregate_features(conn):
    # Загрузка RFM
    rfm = pd.read_sql('SELECT * FROM rfm_segments', conn)
    
    # Ежемесячная агрегация транзакций
    query = '''
        SELECT 
            strftime('%Y-%m', transaction_date) AS month,
            COUNT(DISTINCT customer_id) AS active_customers,
            COUNT(*) AS total_transactions,
            AVG(amount) AS avg_transaction_amount,
            SUM(amount) AS total_revenue_monthly
        FROM transactions
        GROUP BY month
        ORDER BY month
    '''
    
    features = pd.read_sql(query, conn)
    
    # Добавление сегментных метрик (количество клиентов в каждом сегменте)
    segment_counts = rfm.groupby('segment_name').size().reset_index(name='count')
    for _, row in segment_counts.iterrows():
        features[f'{row["segment_name"]}_count'] = row['count']
    
    # Добавление денежного потока
    cashflow = pd.read_sql('SELECT * FROM cashflow', conn)
    cashflow['month'] = pd.to_datetime(cashflow['date']).dt.strftime('%Y-%m')
    monthly_cashflow = cashflow.groupby('month')['total_revenue'].sum().reset_index()
    monthly_cashflow.columns = ['month', 'monthly_cashflow']
    
    features = features.merge(monthly_cashflow, on='month', how='left')
    
    # ============================================
    # СОЗДАНИЕ ЛАГОВЫХ ПРИЗНАКОВ (только 1 лаг, чтобы сохранить больше строк)
    # ============================================
    for i in range(1, 2):
        features[f'lag_{i}_cashflow'] = features['monthly_cashflow'].shift(i)
        features[f'lag_{i}_active'] = features['active_customers'].shift(i)
        features[f'lag_{i}_avg_transaction'] = features['avg_transaction_amount'].shift(i)
    
    # Удаление строки с NaN (первые N месяцев, где N = количество лагов)
    features = features.dropna()
    print(f"После удаления NaN (лаги): {len(features)} строк")
    
    if len(features) < 3:
        print("ПРЕДУПРЕЖДЕНИЕ: слишком мало строк для обучения модели. Увеличьте данные или уменьшите количество лагов.")
    
    # Сохранение
    features.to_csv('data/processed/features.csv', index=False)
    print("[OK] Признаки созданы и сохранены в data/processed/features.csv")
    return features

if __name__ == '__main__':
    conn = sqlite3.connect(db_path)
    features = aggregate_features(conn)
    print(f"\nПервые 5 строк:\n{features.head()}")
    print(f"\nРазмер датасета: {features.shape}")