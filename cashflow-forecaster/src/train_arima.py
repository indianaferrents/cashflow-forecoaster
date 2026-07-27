import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# ============================================
# ЗАГРУЗКА ДАННЫХ
# ============================================
df = pd.read_csv('data/processed/features.csv')
print(f"Загружено {len(df)} строк")

target = 'monthly_cashflow'
y = df[target]

# Разделение
# Использование последних test_months для теста (значение передаётся из командной строки)
import sys
test_months = 4
if len(sys.argv) > 1:
    test_months = int(sys.argv[1])

test_size = min(test_months, len(y) - 1)
if test_size < 1:
    test_size = 1

y_train = y[:-test_size]
y_test = y[-test_size:]

print(f"Обучающая выборка: {len(y_train)} строк")
print(f"Тестовая выборка: {len(y_test)} строк")

# ============================================
# ОБУЧЕНИЕ ARIMA
# ============================================
# Подборка параметров (p,d,q) по AIC
best_aic = np.inf
best_order = None
best_model = None

for p in range(0, 4):
    for d in range(0, 2):
        for q in range(0, 4):
            try:
                model = ARIMA(y_train, order=(p, d, q))
                fitted = model.fit()
                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_order = (p, d, q)
                    best_model = fitted
            except:
                continue

if best_model is None:
    best_model = ARIMA(y_train, order=(1,0,0)).fit()

print(f"Лучшая ARIMA: order={best_order}, AIC={best_aic:.2f}")

# Прогноз
y_pred = best_model.forecast(steps=len(y_test))

# Метрики
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n--- ARIMA Метрики ---")
print(f"MAE: {mae:,.2f}")
print(f"RMSE: {rmse:,.2f}")
print(f"Коэффициент детерминации: {r2:.4f}")

# Сохранение результатов
results = pd.DataFrame({
    'Модель': ['ARIMA'],
    'MAE': [mae],
    'RMSE': [rmse],
    'Коэффициент детерминации': [r2]
})
results.to_csv('reports/arima_metrics.csv', index=False)

# Сохранение прогнозов
test_results = pd.DataFrame({
    'actual': y_test.values,
    'arima_pred': y_pred
})
test_results.to_csv('reports/arima_predictions.csv', index=False)

print("[OK] ARIMA результаты сохранены")