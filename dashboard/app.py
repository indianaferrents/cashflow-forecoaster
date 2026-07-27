import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import os
import subprocess
import sys
from datetime import datetime
import numpy as np
from sklearn.metrics import r2_score

# ============================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================
st.set_page_config(
    page_title="CashFlow Forecaster",
    page_icon="dashboard/icon.ico",
    layout="wide"
)

# ============================================
# CSS
# ============================================
st.markdown("""
<style>
    .stAppDeployButton {
        visibility: hidden;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {
        background: transparent !important;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    [data-testid="stStatusWidget"] {
        visibility: hidden;
    }
    .stStopButton {
        visibility: hidden;
    }
    div[data-testid="stStatusWidget"] div {
        visibility: hidden;
    }
    div[data-testid="stToast"] {
    position: fixed !important;
    top: 5px !important;
    right: 9px !important;
    z-index: 999999 !important;
    width: auto !important;
    max-width: 400px !important;
    color: #fff !important;
    border-radius: 8px !important;
    padding: 12px 20px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

st.image("dashboard/logo.png", width=400)

if 'db_path' not in st.session_state:
    st.session_state.db_path = 'data/cashflow.db'

# ============================================
# БОКОВАЯ ПАНЕЛЬ
# ============================================
st.sidebar.header("⚙️ Панель управления")

# ---------- 1. Генерация данных ----------
st.sidebar.subheader("1. Генерация данных")

n_customers = st.sidebar.number_input(
    "Количество клиентов",
    min_value=1000,
    max_value=1000000,
    value=1000,
    step=1000,
    help="Чем больше клиентов, тем реалистичнее данные."
)

n_transactions = st.sidebar.number_input(
    "Количество транзакций",
    min_value=10000,
    max_value=10000000,
    value=10000,
    step=10000,
    help="Общее количество покупок за период."
)

start_date = st.sidebar.date_input(
    "Начальная дата",
    value=datetime(2020, 1, 1)
)

end_date = st.sidebar.date_input(
    "Конечная дата",
    value=datetime(2025, 12, 31)
)

if st.sidebar.button("🔄 Сгенерировать новые данные", type="primary"):
    with st.toast("⏳ Генерация данных... Это может занять несколько минут..."):
        cmd = [
            sys.executable,
            "src/data_generator.py",
            str(n_customers),
            str(n_transactions),
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            st.toast("✅ Данные сгенерированы!")
        else:
            st.toast(f"❌ Ошибка: {result.stderr}")

st.sidebar.divider()

# ---------- 2. Загрузка своей БД ----------
st.sidebar.subheader("2. Загрузка своей БД")

uploaded_file = st.sidebar.file_uploader(
    "Загрузите SQLite базу данных",
    type=['db', 'sqlite', 'sqlite3'],
    help="""
**Требования к загружаемой базе данных:**
- **Она должна содержать три обязательные таблицы**:
  - `customers` (поля: `customer_id`, `registration_date`, `region`, `segment`)
  - `transactions` (поля: `transaction_id`, `customer_id`, `transaction_date`, `amount`, `payment_method`)
  - `cashflow` (поля: `date`, `total_revenue`)
- **С такими типами данных:**
  - `DATE` – для дат (`registration_date`, `transaction_date`, `date`)
  - `DECIMAL` – для денежных сумм (`amount`, `total_revenue`)
  - `INTEGER` – для идентификаторов (`customer_id`, `transaction_id`)
  - `VARCHAR` – для текстовых полей (`region`, `segment`, `payment_method`)
- Подробное описание структуры приведено в файле `sql/schema.sql` и в `README.md`.
"""
)

if uploaded_file:
    with open("data/uploaded.db", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success("✅ БД загружена!")
    st.sidebar.info("Укажите количество месяцев для теста, поставьте галочку **«Использовать загруженную БД»** и нажмите **«Запустить прогноз»** ниже")

st.sidebar.divider()

# ---------- 3. Запуск прогноза ----------
st.sidebar.subheader("3. Запуск прогноза")

test_months = st.sidebar.number_input(
    "Количество месяцев для теста",
    min_value=1,
    max_value=None,
    value=6,
    help="Сколько последних месяцев использовать для проверки модели. Если вы выставите больше месяцев для теста, чем загрузили, то модель будет использовать все загруженные, кроме первого. Это означает, что если вы выберете, например, 100 месяцев, а данных всего 50 — будет использовано 49 месяцев (все, кроме одной для обучения)."
)

use_uploaded = st.sidebar.checkbox(
    "Использовать загруженную БД",
    disabled=not uploaded_file
)

if st.sidebar.button("🚀 Запустить прогноз", type="primary"):
    # ----- Проверки -----
    data_exists = os.path.exists('data/raw/customers.csv') or os.path.exists('data/raw/transactions.csv')
    
    if not data_exists and uploaded_file is None:
        st.sidebar.warning("⚠️ Нет данных для прогноза. Сгенерируйте данные (кнопка «Сгенерировать новые данные») или загрузите свою БД.")
    elif uploaded_file is not None and not use_uploaded:
        st.sidebar.warning("☑️ Поставьте галочку «Использовать загруженную БД» перед запуском прогноза.")
    else:
        st.toast("⏳ Выполняется ETL и обучение модели...")
        st.session_state.db_path = "data/uploaded.db" if use_uploaded and uploaded_file else "data/cashflow.db"
        db_path = st.session_state.db_path
        # ETL
        cmd_etl = [sys.executable, "src/etl.py", db_path]
        result_etl = subprocess.run(cmd_etl, capture_output=True, text=True)
        if result_etl.returncode != 0:
            st.sidebar.error(f"Ошибка ETL: {result_etl.stderr}")
            st.stop()
        
        # Feature Engineering
        cmd_features = [sys.executable, "src/features.py", db_path]
        result_features = subprocess.run(cmd_features, capture_output=True, text=True)
        if result_features.returncode != 0:
            st.sidebar.error(f"Ошибка Feature Engineering: {result_features.stderr}")
            st.stop()
        
        ## Обучение модели (передаём количество месяцев для теста)
        cmd_train = [sys.executable, "src/train_xgboost.py", str(test_months)]
        result_train = subprocess.run(cmd_train, capture_output=True, text=True)
        if result_train.returncode != 0:
            st.sidebar.error(f"Ошибка обучения модели: {result_train.stderr}")
            st.stop()
        
        st.toast("✅ Прогноз выполнен успешно!")

st.sidebar.divider()

# ---------- 4. Сравнение моделей ----------
st.sidebar.subheader("4 Сравнение моделей")

st.sidebar.caption(
    "Запуск процесса сравнения моделей ARIMA и LSTM с моделью XGBoost, вывод графика сравнения, лучшей модели и аналитики прогноза по ней."
)

if st.sidebar.button("🔬 Запустить сравнение ARIMA | LSTM", type="secondary"):
    # Проверка, есть ли результаты прогноза
    if not os.path.exists('reports/xgboost_metrics.csv'):
        st.sidebar.warning("⚠️ Сначала выполните прогноз (кнопка «Запустить прогноз»), чтобы получить данные для сравнения.")
    else:
        st.toast("⏳ Запуск сравнения моделей...")
        # ARIMA
        cmd_arima = [sys.executable, "src/train_arima.py", str(test_months)]
        result_arima = subprocess.run(cmd_arima, capture_output=True, text=True)
        if result_arima.returncode != 0:
            st.sidebar.error(f"Ошибка ARIMA: {result_arima.stderr}")
        
        # LSTM
        cmd_lstm = [sys.executable, "src/train_lstm.py", str(test_months)]
        result_lstm = subprocess.run(cmd_lstm, capture_output=True, text=True)
        if result_lstm.returncode != 0:
            st.sidebar.error(f"Ошибка LSTM: {result_lstm.stderr}")
        
        st.toast("✅ Сравнение завершено!")

st.sidebar.divider()

# ---------- 5. Сохранение данных ----------
st.sidebar.subheader("5. Сохранение данных")

save_dir = st.sidebar.text_input(
    "Папка для сохранения",
    value="saved_data_reports",
    help="Укажите имя папки для сохранения data и reports (она будет создана в корневой папке)."
)

if st.sidebar.button("💾 Сохранить данные и результаты", type="secondary"):
    import shutil
    import os
    from datetime import datetime
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(save_dir, f"backup_{timestamp}")
        os.makedirs(save_path, exist_ok=True)
        
        # Сохранение data
        if os.path.exists('data'):
            data_path = os.path.join(save_path, 'data')
            if os.path.exists(data_path):
                shutil.rmtree(data_path)
            shutil.copytree('data', data_path)
            st.sidebar.write(f"✅ data/ → {data_path}")
        
        # Сохранение reports
        if os.path.exists('reports'):
            reports_path = os.path.join(save_path, 'reports')
            if os.path.exists(reports_path):
                shutil.rmtree(reports_path)
            shutil.copytree('reports', reports_path)
            st.sidebar.write(f"✅ reports/ → {reports_path}")
        
        st.sidebar.success(f"✅ Данные сохранены в: {save_path}")
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка сохранения: {e}")

st.sidebar.divider()

# ---------- 6. Очистка данных ----------
st.sidebar.subheader("6. Очистка данных")

st.sidebar.caption(
    "При нажатии на кнопку произойдет удаление всех сгенерированных данных, БД, отчётов и загруженных файлов из корневой папки. Операция необратима, убедитесь, что сохраниили все в папку для сохранения!"
)

if st.sidebar.button("🗑️ Очистить все данные", type="secondary"):
    import shutil
    import os
    import time
    
    try:
        # Удаление БД
        if os.path.exists('data/cashflow.db'):
            os.remove('data/cashflow.db')
        
        # Удаление сырых данных
        if os.path.exists('data/raw'):
            for f in os.listdir('data/raw'):
                os.remove(os.path.join('data/raw', f))
        
        # Удаление обработанных данных
        if os.path.exists('data/processed'):
            for f in os.listdir('data/processed'):
                os.remove(os.path.join('data/processed', f))
        
        # Удаление отчетов
        if os.path.exists('reports'):
            for f in os.listdir('reports'):
                file_path = os.path.join('reports', f)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        # Удаление загруженной БД
        if os.path.exists('data/uploaded.db'):
            os.remove('data/uploaded.db')
        
        st.sidebar.success("✅ Все данные очищены!")
        time.sleep(3)
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка очистки: {e}")
        time.sleep(3)
        st.rerun()

# ============================================
# ОСНОВНАЯ ОБЛАСТЬ — РЕЗУЛЬТАТЫ
# ============================================
best_model = None 

if os.path.exists('data/processed/features.csv') and os.path.exists('reports/xgboost_metrics.csv'):
    st.title("📊 Результаты прогноза XGBoost")

if os.path.exists('data/processed/features.csv') and os.path.exists('reports/xgboost_metrics.csv'):
    
    df = pd.read_csv('data/processed/features.csv')
    metrics = pd.read_csv('reports/xgboost_metrics.csv')
    
    # ----- Метрики -----
    st.subheader("📈 Метрики качества модели")
    
    col1, col2, col3 = st.columns(3)
    
    mae_val = metrics[metrics['metric'] == 'MAE']['value'].values[0]
    rmse_val = metrics[metrics['metric'] == 'RMSE']['value'].values[0]
    r2_val = metrics[metrics['metric'] == 'Коэффициент детерминации']['value'].values[0]
    
    col1.metric("MAE", f"{mae_val:,.0f} ₽")
    col2.metric("RMSE", f"{rmse_val:,.0f} ₽")
    col3.metric("Коэффициент детерминации", f"{r2_val:.4f}")
    
    # ----- Визуализация -----
    st.subheader("📉 Визуализация")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists('reports/feature_importance.png'):
            st.image('reports/feature_importance.png', caption='Важность признаков')
        else:
            st.warning("График важности признаков не найден")
    
    with col2:
        if os.path.exists('reports/prediction_vs_actual.png'):
            st.image('reports/prediction_vs_actual.png', caption='Прогноз vs Факт')
        else:
            st.warning("График прогноза не найден")

        # ----- Расширенная аналитика по прогнозу -----
    st.subheader("📊 Аналитика прогноза")
    
    try:
        test_df = pd.read_csv('reports/xgboost_results.csv')
        
        if len(test_df) > 0:
            # Основные показатели
            last_actual = test_df['actual'].iloc[-1]
            last_pred = test_df['predicted'].iloc[-1]
            first_actual = test_df['actual'].iloc[0]
            first_pred = test_df['predicted'].iloc[0]
            
            # Изменения
            change = last_pred - last_actual
            change_pct = (change / last_actual) * 100 if last_actual != 0 else 0
            total_change = last_actual - first_actual
            total_change_pct = (total_change / first_actual) * 100 if first_actual != 0 else 0
            
            # Ошибки
            errors = abs(test_df['actual'] - test_df['predicted'])
            max_error = errors.max()
            min_error = errors.min()
            avg_error = errors.mean()
            
            # Точность прогноза (1 - MAPE)
            mape = (errors / test_df['actual']).mean() * 100
            accuracy = max(0, 100 - mape)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "📈 Прогноз на следующий месяц",
                    f"{last_pred:,.0f} ₽",
                    delta=f"{change:+,.0f} ₽ ({change_pct:+.1f}%)"
                )
                st.caption(f"Факт за последний месяц: {last_actual:,.0f} ₽")
            
            with col2:
                st.metric(
                    "🎯 Точность прогноза",
                    f"{accuracy:.1f}%",
                    delta=f"MAE: {avg_error:,.0f} ₽"
                )
                st.caption(f"Ошибка: от {min_error:,.0f} до {max_error:,.0f} ₽")
            
            with col3:
                trend_icon = "📈" if total_change > 0 else "📉" if total_change < 0 else "➡️"
                st.metric(
                    f"{trend_icon} Изменение за период",
                    f"{total_change:+,.0f} ₽",
                    delta=f"{total_change_pct:+.1f}% за {len(test_df)} месяцев"
                )
                st.caption(f"С {first_actual:,.0f} ₽ до {last_actual:,.0f} ₽")
            
            # --- Дополнительные инсайты ---
            st.divider()
            
            st.markdown("**🔍 Ключевые выводы:**")

            if change_pct > 5:
                 st.success(f"✅ Прогнозируется **рост** денежного потока на **{change_pct:.1f}%**")
            elif change_pct < -5:
                st.warning(f"⚠️ Прогнозируется **снижение** денежного потока на **{abs(change_pct):.1f}%**")
            else:
                st.info(f"➡️ Прогнозируется **стабильность** денежного потока (±{abs(change_pct):.1f}%)")

            if accuracy > 85:
                st.success(f"✅ Модель показывает **высокую точность** ({accuracy:.1f}%)")
            elif accuracy > 70:
                st.info(f"📊 Модель показывает **среднюю точность** ({accuracy:.1f}%)")
            else:
                st.warning(f"⚠️ Точность модели **ниже ожидаемой** ({accuracy:.1f}%)")
            
            st.markdown("**🏆 Ключевые драйверы прогноза**")
            st.caption("Признаки, которые сильнее всего влияют на прогноз денежного потока")

            try:
                importance_df = pd.read_csv('reports/feature_importance.csv')
                if len(importance_df) > 0:
                    top_5 = importance_df.head(5)
        
                    for i, (_, row) in enumerate(top_5.iterrows()):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            # Иконка в зависимости от важности
                            if row['importance'] > 0.5:
                                icon = "🔥"
                            elif row['importance'] > 0.2:
                                icon = "📊"
                            else:
                                icon = "📌"
                            st.markdown(f"**{icon} {row['feature']}**")
                        with col2:
                            # Прогресс-бар
                            color = "#28a745" if row['importance'] > 0.5 else "#ffc107" if row['importance'] > 0.2 else "#17a2b8"
                            st.markdown(f"""
                            <div style="background-color: #e9ecef; border-radius: 4px; height: 8px; width: 100%;">
                                <div style="background-color: {color}; height: 8px; border-radius: 4px; width: {row['importance']*100:.0f}%;"></div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col3:
                            st.markdown(f"**<span style='color:{color};'>{row['importance']:.1%}</span>**", unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Ошибка загрузки важности признаков: {e}")
            
            # --- Рекомендации ---
            st.divider()
            st.markdown("**💡 Рекомендации:**")
            
            if change_pct < -5:
                st.markdown("""
                - 📉 Ожидается снижение денежного потока. Рекомендуется:
                  - Усилить работу с ключевыми клиентами
                  - Проверить дебиторскую задолженность
                  - Рассмотреть возможность отсрочки крупных платежей
                """)
            elif change_pct > 5:
                st.markdown("""
                - 📈 Ожидается рост денежного потока. Рекомендуется:
                  - Направить дополнительные средства на развитие
                  - Рассмотреть инвестиционные возможности
                  - Усилить маркетинговую активность
                """)
            else:
                st.markdown("""
                - ➡️ Прогнозируется стабильный денежный поток. Рекомендуется:
                  - Поддерживать текущий уровень активности
                  - Мониторить ключевые показатели
                  - Подготовить план действий при изменении ситуации
                """)
            
            # Дополнительная информация
            st.caption(f"📊 Аналитика основана на **{len(test_df)} месяцах** тестовой выборки")
            
        else:
            st.info("Нет данных для аналитики.")
            
    except FileNotFoundError:
        st.info("Тестовые результаты пока не сохранены. Запустите прогноз.")
    
        # ----- Сравнение моделей -----
    if os.path.exists('reports/arima_metrics.csv') and os.path.exists('reports/lstm_metrics.csv'):
        st.subheader("📊 Сравнение моделей")
        
        arima = pd.read_csv('reports/arima_metrics.csv')
        lstm = pd.read_csv('reports/lstm_metrics.csv')
        xgb_metrics = pd.read_csv('reports/xgboost_metrics.csv')
        
        # Сбор информации
        xgb_row = pd.DataFrame({
            'Модель': ['XGBoost'],
            'MAE': [xgb_metrics[xgb_metrics['metric']=='MAE']['value'].values[0]],
            'RMSE': [xgb_metrics[xgb_metrics['metric']=='RMSE']['value'].values[0]],
            'Коэффициент детерминации': [xgb_metrics[xgb_metrics['metric']=='Коэффициент детерминации']['value'].values[0]]
        })
        
        comparison = pd.concat([xgb_row, arima, lstm], ignore_index=True)
        
        # Вывод таблицы
        st.dataframe(comparison, use_container_width=True)
        
        # График сравнения
        fig, ax = plt.subplots(figsize=(6, 3))
        comparison.set_index('Модель')[['MAE', 'RMSE']].plot(kind='bar', ax=ax)
        ax.set_title('Сравнение моделей по ошибкам')
        ax.set_ylabel('Ошибка')
        ax.legend()
        st.pyplot(fig)
        
        # Лучшая модель
        best_idx = comparison['MAE'].idxmin()
        best_model = comparison.iloc[best_idx]['Модель']
        st.success(f"🏆 Лучшая модель по MAE: **{best_model}**")
    else:
        st.info("Нажмите **«Запустить сравнение ARIMA | LSTM»** в боковой панели, чтобы увидеть сравнение.")

    # ----- Детальный анализ прогноза лучшей модели -----
    if best_model is not None and best_model != 'XGBoost':
        # Определение файла и колонки для лучшей модели
        if best_model == 'ARIMA':
            pred_file = 'reports/arima_predictions.csv'
            pred_col = 'arima_pred'
            model_label = 'ARIMA'
            model_desc = "ARIMA — классическая статистическая модель для временных рядов. Хорошо работает на коротких периодах, но не учитывает внешние факторы."
        elif best_model == 'LSTM':
            pred_file = 'reports/lstm_predictions.csv'
            pred_col = 'lstm_pred'
            model_label = 'LSTM'
            model_desc = "LSTM — рекуррентная нейросеть, способная улавливать долгосрочные зависимости. Требует больше данных, но может давать более точные прогнозы."
        else:
            pred_file = None
            pred_col = None
        
        if pred_file and os.path.exists(pred_file):
            st.divider()
            st.title(f"📊 Детальный анализ прогноза модели {model_label}")
            
            try:
                best_df = pd.read_csv(pred_file)
                
                # Проверка наличия колонок
                if 'actual' not in best_df.columns:
                    st.warning(f"В файле {pred_file} нет колонки 'actual'")
                elif pred_col not in best_df.columns:
                    st.warning(f"В файле {pred_file} нет колонки '{pred_col}'")
                else:
                    # Переименовывание для единообразия
                    best_df = best_df.rename(columns={pred_col: 'predicted'})
                    # Удаление строки с NaN
                    best_df = best_df.dropna(subset=['actual', 'predicted'])
                    
                    if len(best_df) == 0:
                        st.warning("Нет данных для анализа.")
                    else:
                        # Основные показатели
                        last_actual = best_df['actual'].iloc[-1]
                        last_pred = best_df['predicted'].iloc[-1]
                        first_actual = best_df['actual'].iloc[0]
                        
                        change = last_pred - last_actual
                        change_pct = (change / last_actual) * 100 if last_actual != 0 else 0
                        total_change = last_actual - first_actual
                        total_change_pct = (total_change / first_actual) * 100 if first_actual != 0 else 0
                        
                        errors = abs(best_df['actual'] - best_df['predicted'])
                        avg_error = errors.mean()
                        mape = (errors / best_df['actual']).mean() * 100
                        accuracy = max(0, 100 - mape)
                        
                        # Метрики для лучшей модели
                        best_mae = avg_error
                        best_rmse = np.sqrt(((best_df['actual'] - best_df['predicted']) ** 2).mean())
                        best_r2 = r2_score(best_df['actual'], best_df['predicted'])
                        
                        # Отображение метрик
                        col1, col2, col3 = st.columns(3)
                        col1.metric("MAE", f"{best_mae:,.0f} ₽")
                        col2.metric("RMSE", f"{best_rmse:,.0f} ₽")
                        col3.metric("Коэффициент детерминации", f"{best_r2:.4f}")
                        
                        # Краткие выводы
                        st.markdown(f"**🔍 Ключевые выводы для модели {model_label}:**")
                        col1, col2 = st.columns(2)
                        with col1:
                            if change_pct > 5:
                                st.success(f"📈 Прогнозируется **рост** денежного потока на **{change_pct:.1f}%**")
                            elif change_pct < -5:
                                st.warning(f"📉 Прогнозируется **снижение** денежного потока на **{abs(change_pct):.1f}%**")
                            else:
                                st.info(f"➡️ Прогнозируется **стабильность** (±{abs(change_pct):.1f}%)")
                            
                            if accuracy > 85:
                                st.success(f"✅ Точность прогноза: **{accuracy:.1f}%**")
                            elif accuracy > 70:
                                st.info(f"📊 Точность прогноза: **{accuracy:.1f}%**")
                            else:
                                st.warning(f"⚠️ Точность прогноза: **{accuracy:.1f}%**")
                        with col2:
                            st.caption(f"📅 Прогноз на следующий месяц: **{last_pred:,.0f} ₽**")
                            st.caption(f"📊 Изменение за период: **{total_change:+,.0f} ₽** ({total_change_pct:+.1f}%)")
                            st.caption(f"📉 Средняя ошибка (MAE): **{avg_error:,.0f} ₽**")
                        
                        # ---- Дополнительная информация о модели ----
                        st.markdown(f"**ℹ️ О модели {model_label}**")
                        st.caption(model_desc)
                        
                        # ---- Таблица сравнения (последние 6 месяцев) ----
                        st.markdown(f"**📋 Сравнение фактических и прогнозных значений (последние {min(6, len(best_df))} месяцев)**")
                        last_n = min(6, len(best_df))
                        compare_df = best_df.tail(last_n).reset_index(drop=True)
                        compare_df.index = [f"Месяц {i+1}" for i in range(len(compare_df))]
                        st.dataframe(compare_df[['actual', 'predicted']].style.format("{:,.0f}"), use_container_width=True)
                        
                        # ---- График прогноза лучшей модели ----
                        st.markdown(f"**📈 График прогноза модели {model_label}**")
                        fig_best, ax_best = plt.subplots(figsize=(10, 5))
                        ax_best.plot(best_df['actual'], label='Факт', marker='o', linestyle='-')
                        ax_best.plot(best_df['predicted'], label=f'Прогноз ({model_label})', marker='x', linestyle='--')
                        ax_best.legend()
                        ax_best.set_title(f'Прогноз vs Факт ({model_label})')
                        ax_best.set_xlabel('Период (индекс)')
                        ax_best.set_ylabel('Денежный поток')
                        ax_best.grid(True, alpha=0.3)
                        st.pyplot(fig_best)
                        
                        # ---- Примечание о признаках ----
                        st.caption("**Примечание:** ARIMA и LSTM не предоставляют важность признаков, в отличие от XGBoost. Анализ драйверов доступен только для XGBoost.")
                        
            except Exception as e:
                st.warning(f"Ошибка при анализе прогноза {model_label}: {e}")

    # ----- Сравнение прогнозов XGBoost и лучшей модели -----
    if best_model is not None and best_model != 'XGBoost':
        st.divider()
        st.subheader(f"📈 Сравнение прогноза XGBoost c {best_model}")
        
        xgb_pred_file = 'reports/xgboost_results.csv'
        if os.path.exists(xgb_pred_file) and pred_file and os.path.exists(pred_file):
            try:
                xgb_df = pd.read_csv(xgb_pred_file)
                best_df = pd.read_csv(pred_file)
                
                # Переименовывание колонки для лучшей модели
                if pred_col in best_df.columns:
                    best_df = best_df.rename(columns={pred_col: 'predicted'})
                elif 'predicted' not in best_df.columns:
                    st.warning(f"В файле {pred_file} нет колонки 'predicted' или '{pred_col}'")
                else:
                    pass
                
                # Удаление NaN
                xgb_df = xgb_df.dropna(subset=['actual', 'predicted'])
                best_df = best_df.dropna(subset=['actual', 'predicted'])
                
                # Обрезание до минимальной длины
                min_len = min(len(xgb_df), len(best_df))
                if min_len == 0:
                    st.warning("Нет данных для сравнения.")
                else:
                    xgb_df = xgb_df.iloc[:min_len]
                    best_df = best_df.iloc[:min_len]
                    
                    # Вывод обеих прогнозов на одном графике
                    fig_comp, ax_comp = plt.subplots(figsize=(12, 6))
                    ax_comp.plot(xgb_df['actual'], label='Факт', marker='o', linestyle='-', color='black', linewidth=2)
                    ax_comp.plot(xgb_df['predicted'], label='XGBoost', marker='s', linestyle='--', color='blue')
                    ax_comp.plot(best_df['predicted'], label=best_model, marker='^', linestyle='--', color='green')
                    ax_comp.legend()
                    ax_comp.set_title('Сравнение прогнозов моделей')
                    ax_comp.set_xlabel('Период (индекс)')
                    ax_comp.set_ylabel('Денежный поток')
                    ax_comp.grid(True, alpha=0.3)
                    st.pyplot(fig_comp)
                    
                    # Сравнительная таблица ошибок
                    st.markdown("**📊 Сравнение ошибок прогнозов**")
                    xgb_errors = abs(xgb_df['actual'] - xgb_df['predicted'])
                    best_errors = abs(best_df['actual'] - best_df['predicted'])
                    comp_df = pd.DataFrame({
                        'Метрика': ['MAE', 'RMSE', 'MAPE (%)'],
                        'XGBoost': [
                            f"{xgb_errors.mean():,.0f}",
                            f"{np.sqrt((xgb_df['actual'] - xgb_df['predicted'])**2).mean():,.0f}",
                            f"{(xgb_errors / xgb_df['actual']).mean()*100:.1f}"
                        ],
                        best_model: [
                            f"{best_errors.mean():,.0f}",
                            f"{np.sqrt((best_df['actual'] - best_df['predicted'])**2).mean():,.0f}",
                            f"{(best_errors / best_df['actual']).mean()*100:.1f}"
                        ]
                    })
                    st.dataframe(comp_df, use_container_width=True)
                    
                    # Вывод о лучшей модели
                    if best_errors.mean() < xgb_errors.mean():
                        st.success(f"🏆 **{best_model}** показывает меньшую среднюю ошибку (MAE) и может быть предпочтительнее.")
                    else:
                        st.info(f"📊 **XGBoost** показывает меньшую среднюю ошибку (MAE) по сравнению с {best_model}.")
            except Exception as e:
                st.warning(f"Ошибка при сравнении прогнозов: {e}")

    # ----- Просмотр БД -----
    st.subheader("🗄️ Просмотр базы данных")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Транзакции", "Клиенты", "Денежный поток", "RFM-сегменты"])
    
    try:
        conn = sqlite3.connect(st.session_state.db_path)
        
        with tab1:
            df_trans = pd.read_sql('SELECT * FROM transactions LIMIT 100', conn)
            st.dataframe(df_trans)
            st.caption(f"Показано {len(df_trans)} записей из таблицы transactions")
        
        with tab2:
            df_cust = pd.read_sql('SELECT * FROM customers LIMIT 100', conn)
            st.dataframe(df_cust)
            st.caption(f"Показано {len(df_cust)} записей из таблицы customers")
        
        with tab3:
            df_cash = pd.read_sql('SELECT * FROM cashflow LIMIT 100', conn)
            st.dataframe(df_cash)
            st.caption(f"Показано {len(df_cash)} записей из таблицы cashflow")
        
        with tab4:
            try:
                df_rfm = pd.read_sql('SELECT * FROM rfm_segments LIMIT 100', conn)
                st.dataframe(df_rfm)
                st.caption(f"Показано {len(df_rfm)} записей из таблицы rfm_segments")
            except:
                st.info("Таблица rfm_segments пока не создана. Запустите прогноз.")
        
        conn.close()
    except Exception as e:
        st.error(f"Ошибка при загрузке БД: {e}")
    
    # ----- Исходные данные -----
    st.subheader("📋 Данные для прогноза (признаки)")
    st.dataframe(df)
    st.caption(f"Всего {len(df)} записей, {len(df.columns)} колонок")

        # ----- Справочная информация (признаки) -----
    st.subheader("📖 Справочник (обозначение признаков)")
    
    features_info = pd.DataFrame({
        '№': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        'Название в коде': [
            'active_customers', 'total_transactions', 'avg_transaction_amount', 
            'total_revenue_monthly', 'lag_1_cashflow', 'lag_1_active', 
            'lag_1_avg_transaction', 'Champions_count', 'Loyal_count', 
            'At Risk_count', 'Others_count', 'monthly_cashflow', 'month'
        ],
        'Понятное название': [
            'Активные клиенты', 'Общее число транзакций', 'Средний чек',
            'Выручка за месяц', 'Денежный поток (месяц назад)',
            'Активные клиенты (месяц назад)', 'Средний чек (месяц назад)',
            'Клиенты «Чемпионы»', 'Клиенты «Лояльные»',
            'Клиенты «Под угрозой»', 'Клиенты «Остальные»',
            'Денежный поток (целевая переменная)', 'Месяц (только для группировки)'
        ],
        'Группа': [
            'Базовый', 'Базовый', 'Базовый',
            'Базовый', 'Лаговый', 'Лаговый',
            'Лаговый', 'RFM-сегмент', 'RFM-сегмент',
            'RFM-сегмент', 'RFM-сегмент', 'Целевая переменная',
            'Не используется'
        ],
        'Используется в модели': [
            '✅', '✅', '✅',
            '✅', '✅', '✅',
            '✅', '✅', '✅',
            '✅', '✅', '❌ (цель)',
            '❌'
        ]
    })
    
    st.dataframe(features_info, use_container_width=True, hide_index=True)
    st.caption("Таблица для справки, все признаки, их значения и использование в модели")

else:
    st.markdown("**Прогнозирование операционного денежного потока компании на основе аналитики клиентских данных**")
    st.markdown("""

    **Этот сервис позволяет:**
    - 📊 **Генерировать** синтетические данные о клиентах и транзакциях
    - 📁 **Загружать** собственную базу данных SQLite
    - 🦾 **Обучать** модель XGBoost для прогнозирования денежного потока
    - 📈 **Сравнивать** модели (XGBoost с ARIMA и LSTM)
    - 📉 **Анализировать** важность признаков и видеть прогноз
    - 💾 **Сохранять** готовые результаты прогноза
    
    """)
    
    st.markdown("""
    **Инструкция:**
    1. В боковой панели настройте параметры
    2. Нажмите **«Сгенерировать новые данные»** или **«Загрузка своей БД»**
    3. Укажите количество месяцев для теста
    4. Нажмите **«Запустить прогноз»**
    5. Нажмите **«Запустить сравнение ARIMA | LSTM»** (опционально)
    6. Результаты появятся здесь
    7. Сохраните и/или очистите данные
    """)