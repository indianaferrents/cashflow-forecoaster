import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping
import warnings
warnings.filterwarnings('ignore')
import sys
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# ============================================
# ЗАГРУЗКА ДАННЫХ
# ============================================
df = pd.read_csv('data/processed/features.csv')
print(f"Загружено {len(df)} строк")

target = 'monthly_cashflow'
y = df[target].values.reshape(-1, 1)

# Нормализация
scaler = MinMaxScaler()
y_scaled = scaler.fit_transform(y)

# Разделение
test_months = 4
if len(sys.argv) > 1:
    test_months = int(sys.argv[1])

test_size = min(test_months, len(y_scaled) - 1)
if test_size < 1:
    test_size = 1

train = y_scaled[:-test_size]
test = y_scaled[-test_size:]

print(f"Обучающая выборка: {len(train)} строк")
print(f"Тестовая выборка: {len(test)} строк")

# ============================================
# ПОДГОТОВКА ДАННЫХ ДЛЯ LSTM (sequence)
# ============================================
def create_sequences(data, seq_length):
    X, y_seq = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y_seq.append(data[i+seq_length])
    return np.array(X), np.array(y_seq)

seq_length = min(3, len(train) - 1)
if seq_length < 1:
    seq_length = 1

X_train, y_train_seq = create_sequences(train, seq_length)
X_test, y_test_seq = create_sequences(test, seq_length)

if len(X_train) == 0 or len(X_test) == 0:
    print("Недостаточно данных для LSTM, пропускаем...")
    # Создание пустого результата
    pd.DataFrame({'Модель': ['LSTM'], 'MAE': [np.nan], 'RMSE': [np.nan], 'Коэффициент детерминации': [np.nan]}).to_csv('reports/lstm_metrics.csv', index=False)
    exit(0)

# ============================================
# ПОСТРОЕНИЕ МОДЕЛИ LSTM
# ============================================
model = Sequential([
    LSTM(50, activation='relu', input_shape=(seq_length, 1)),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')

early_stop = EarlyStopping(monitor='val_loss', patience=10)
model.fit(X_train, y_train_seq, epochs=100, batch_size=8, validation_split=0.1, callbacks=[early_stop], verbose=0)

# Прогноз
y_pred_scaled = model.predict(X_test, verbose=0)
y_pred = scaler.inverse_transform(y_pred_scaled)
y_true = scaler.inverse_transform(y_test_seq)

# Метрики
mae = mean_absolute_error(y_true, y_pred)
rmse = np.sqrt(mean_squared_error(y_true, y_pred))
r2 = r2_score(y_true, y_pred)

print("\n--- LSTM Метрики ---")
print(f"MAE: {mae:,.2f}")
print(f"RMSE: {rmse:,.2f}")
print(f"Коэффициент детерминации: {r2:.4f}")

# Сохранение результата
results = pd.DataFrame({
    'Модель': ['LSTM'],
    'MAE': [mae],
    'RMSE': [rmse],
    'Коэффициент детерминации': [r2]
})
results.to_csv('reports/lstm_metrics.csv', index=False)

# Сохранение прогноза
test_results = pd.DataFrame({
    'actual': y_true.flatten(),
    'lstm_pred': y_pred.flatten()
})
test_results.to_csv('reports/lstm_predictions.csv', index=False)

print("[OK] LSTM результаты сохранены")