import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import os
import shutil
warnings.filterwarnings('ignore')
import sys

# ============================================
# ПАРАМЕТРЫ ИЗ КОМАНДНОЙ СТРОКИ
# ============================================
os.makedirs('reports', exist_ok=True)
test_months = 6   # значение по умолчанию
if len(sys.argv) > 1:
    try:
        test_months = int(sys.argv[1])
        if test_months < 1:
            test_months = 1
    except:
        test_months = 6

print(f"Тестовых месяцев: {test_months}")

# ============================================
# ЗАГРУЗКА ДАННЫХ С ПРИВЕДЕНИЕМ ТИПОВ
# ============================================
df = pd.read_csv('data/processed/features.csv')
print(f"Загружено {len(df)} строк, {len(df.columns)} колонок")

# Привод всех колонок (кроме month) к числовому типу
for col in df.columns:
    if col != 'month':
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Удаление строки с NaN (если появились после приведения типов)
df = df.dropna()
print(f"После приведения типов: {len(df)} строк")

# ============================================
# ПРОВЕРКА: ДОСТАТОЧНО ЛИ ДАННЫХ
# ============================================
if len(df) < 5:
    print("ОШИБКА: Слишком мало данных для обучения модели (нужно минимум 5 строк)")
    print(f"Сейчас доступно: {len(df)} строк")
    print("Пожалуйста, сгенерируйте больше данных или загрузите БД с большим периодом")
    exit(1)

# ============================================
# ПОДГОТОВКА ПРИЗНАКОВ
# ============================================
target = 'monthly_cashflow'
features = [col for col in df.columns if col not in ['month', target]]

X = df[features]
y = df[target]

# ============================================
# РАЗДЕЛЕНИЕ НА ОБУЧЕНИЕ И ТЕСТ (с выбором количества месяцев)
# ============================================
n_samples = len(X)

# Использование введенных пользователем количества месяцев
test_size = min(test_months, n_samples - 1)   # не больше, чем строк минус 1
if test_size < 1:
    test_size = 1

print(f"Фактический размер теста: {test_size} месяцев")

X_train = X[:-test_size]
X_test = X[-test_size:]
y_train = y[:-test_size]
y_test = y[-test_size:]

print(f"Обучающая выборка: {len(X_train)} строк")
print(f"Тестовая выборка: {len(X_test)} строк")

# ============================================
# ОБУЧЕНИЕ МОДЕЛИ
# ============================================
model = xgb.XGBRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    verbosity=0
)
model.fit(X_train, y_train)
print("[OK] Модель обучена")

# ============================================
# ПРОГНОЗ И МЕТРИКИ
# ============================================
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n--- Метрики качества ---")
print(f"MAE: {mae:,.2f}")
print(f"RMSE: {rmse:,.2f}")
print(f"Коэффициент детерминации: {r2:.4f}")

# Сохранение метрик
metrics = pd.DataFrame({
    'metric': ['MAE', 'RMSE', 'Коэффициент детерминации'],
    'value': [mae, rmse, r2]
})
metrics.to_csv('reports/xgboost_metrics.csv', index=False)

# Сохранение фактических и прогнозных значений для аналитики
test_results = pd.DataFrame({
    'actual': y_test.values,
    'predicted': y_pred
})
test_results.to_csv('reports/xgboost_results.csv', index=False)
print("[OK] Тестовые результаты сохранены (reports/xgboost_results.csv)")

# ============================================
# ВАЖНОСТЬ ПРИЗНАКОВ
# ============================================
importance = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

# Сохранение CSV для отображения в интерфейсе
importance.to_csv('reports/feature_importance.csv', index=False)

plt.figure(figsize=(10, 8))
sns.barplot(data=importance.head(10), x='importance', y='feature')
plt.title('Топ-10 важнейших признаков для прогноза')
plt.xlabel('Важность')
plt.ylabel('Признак')
plt.tight_layout()
plt.savefig('reports/feature_importance.png', dpi=150)
print("[OK] График важности признаков сохранён")

# ============================================
# ПРОГНОЗ И ФАКТ
# ============================================
plt.figure(figsize=(10, 8))
plt.plot(y_test.values, label='Факт', marker='o', linestyle='-')
plt.plot(y_pred, label='Прогноз (XGBoost)', marker='x', linestyle='--')
plt.legend()
plt.title('Прогноз и Факт на тестовой выборке')
plt.xlabel('Период (индекс)')
plt.ylabel('Денежный поток')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('reports/prediction_vs_actual.png', dpi=150)
print("[OK] График прогноз и факт сохранён")

# ============================================
# ВЫВОД ТОП-10 ПРИЗНАКОВ
# ============================================
print("\nТоп-10 важнейших признаков:")
for i, row in importance.head(10).iterrows():
    print(f"  {row['feature']}: {row['importance']:.3f}")
