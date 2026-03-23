import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from io import BytesIO

# --- Настройки по умолчанию ---
now = datetime.now()
default_end = now + timedelta(days=7)

st.title("📅 Генератор временных меток")

# --- Боковая панель ---
with st.sidebar:
    st.header("Параметры")
     # Используем "today" для даты начала (Streamlit сам подставит сегодня и разрешит менять)
    start_date = st.date_input("Дата начала", value="today")
    
    # Для времени можно оставить now.time(), но лучше задать фиксированное, например начало дня
    # иначе при каждой смене настроек время будет обновляться на текущие секунды
    start_time = st.time_input("Время начала", value=now.time())

    # Для даты окончания задаем значение по умолчанию, но так как оно вычисляется, 
    # Streamlit не будет его жестко фиксировать
    end_date = st.date_input("Дата окончания", value=default_end.date())
    end_time = st.time_input("Время окончания", value=default_end.time())

    num_entries = st.number_input("Количество объявлений", min_value=1, max_value=10000, value=100)

    st.subheader("Рабочее время")
    work_start_hour = st.number_input("Начало (час)", min_value=0, max_value=23, value=6)
    work_end_hour = st.number_input("Конец (час)", min_value=1, max_value=24, value=23)

    st.subheader("Рабочие дни")
    days_options = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    selected_days = st.multiselect(
        "Выберите рабочие дни",
        options=days_options,
        default=days_options  # Все дни по умолчанию
    )
    day_to_index = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
    work_days = [day_to_index[day] for day in selected_days]

# --- Преобразуем даты ---
start_dt = datetime.combine(start_date, start_time)
end_dt = datetime.combine(end_date, end_time)

if start_dt >= end_dt:
    st.error("Дата начала должна быть раньше даты окончания!")
    st.stop()

# --- Генерация рабочих интервалов ---
def generate_work_intervals(start_dt, end_dt, work_days, work_hours):
    intervals = []
    current = start_dt.date()
    while current <= end_dt.date():
        if current.weekday() in work_days:
            day_start = datetime.combine(current, datetime.min.time()) + timedelta(hours=work_hours[0])
            day_end = datetime.combine(current, datetime.min.time()) + timedelta(hours=work_hours[1])
            interval_start = max(start_dt, day_start)
            interval_end = min(end_dt, day_end)
            if interval_start < interval_end:
                intervals.append((interval_start, interval_end))
        current += timedelta(days=1)
    return intervals

intervals = generate_work_intervals(start_dt, end_dt, work_days, (work_start_hour, work_end_hour))

if not intervals:
    st.warning("Нет рабочего времени в указанном диапазоне.")
    st.stop()

total_seconds = sum((end - start).total_seconds() for start, end in intervals)

# --- Генерация равномерных меток ---
times = []
if num_entries == 1:
    times.append(start_dt)
else:
    for i in range(num_entries):
        progress = i / (num_entries - 1)
        target_seconds = progress * total_seconds
        accumulated = 0
        for (interval_start, interval_end) in intervals:
            duration = (interval_end - interval_start).total_seconds()
            if accumulated + duration >= target_seconds:
                local_time = interval_start + timedelta(seconds=(target_seconds - accumulated))
                times.append(local_time)
                break
            accumulated += duration

# --- Показываем количество ---
st.success(f"Сгенерировано {len(times)} временных меток")

# --- Таблица в интерфейсе ---
df = pd.DataFrame({
    "Дата и время": [t.strftime("%Y-%m-%d %H:%M") for t in times]
})
st.dataframe(df, use_container_width=True)

# --- Кнопка скачивания Excel ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Расписание')
    return output.getvalue()

excel_data = to_excel(df)

st.download_button(
    label="📥 Скачать Excel",
    data=excel_data,
    file_name="расписание_времени.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
