import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import uuid

# Конфигурация
API_URL = "http://localhost:8000/chat"

# Инициализация сессии
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.theme = "Темная"  # По умолчанию

# Настройка страницы
st.set_page_config(
    page_title="RAG-SQL Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Динамическая тема
def get_theme_css(theme):
    if theme == "Темная":
        return """
        <style>
        .stApp { background-color: #0e1117; color: white; }
        .css-1d3910o { background-color: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .chat-message { color: black; }
        .user-message { background-color: #e3f2fd; border-left: 4px solid #2196f3; color: black; }
        .assistant-message { background-color: #f3e5f5; border-left: 4px solid #9c27b0; color: black; }
        .sql-query { background-color: #f5f5f5; color: black; }
        .metric-card { background: white; color: black; }
        .stTextInput > div > div > input { background-color: white !important; color: black !important; }
        .css-1lcbm0y { background-color: #1e2134; color: white; }
        .stButton > button { background-color: #2196f3; color: white; }
        h1, h2, h3, h4, h5, h6 { color: white; }
        p, span, div { color: white; }
        </style>
        """
    else:  # Светлая тема
        return """
        <style>
        .stApp { background-color: #ffffff; color: black; }
        .css-1d3910o { background-color: #f8f9fa; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .chat-message { color: black; }
        .user-message { background-color: #e3f2fd; border-left: 4px solid #2196f3; }
        .assistant-message { background-color: #f3e5f5; border-left: 4px solid #9c27b0; }
        .sql-query { background-color: #f5f5f5; color: black; }
        .metric-card { background: white; color: black; }
        .stTextInput > div > div > input { background-color: white !important; color: black !important; }
        .css-1lcbm0y { background-color: #f8f9fa; color: black; }
        .stButton > button { background-color: #2196f3; color: white; }
        h1, h2, h3, h4, h5, h6 { color: black; }
        p, span, div { color: black; }
        </style>
        """

# Применяем тему
current_theme = st.session_state.get("theme", "Темная")
st.markdown(get_theme_css(current_theme), unsafe_allow_html=True)

# Боковая панель
with st.sidebar:
    st.title("🔧 Настройки")
    
    # Переключатель темы
    theme = st.selectbox(
        "🎨 Тема:",
        ["Светлая", "Темная"],
        index=1 if st.session_state.get("theme", "Темная") == "Темная" else 0
    )
    
    # Обновляем тему если изменилась
    if theme != st.session_state.get("theme", "Темная"):
        st.session_state.theme = theme
        st.rerun()
    
    # Управление сессией
    st.subheader("💬 Сессия")
    current_session = st.text_input(
        "ID сессии:",
        value=st.session_state.session_id,
        help="Уникальный идентификатор вашей сессии"
    )
    
    if st.button("🆕 Новая сессия"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()
    
    # История сессий
    st.subheader("📚 История")
    if st.button("🗑️ Очистить историю"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()
    
    # Информация о системе
    st.subheader("ℹ️ Информация")
    st.info("""
    **RAG-SQL Agent v1.0**
    
    🗄️ **База:** PostgreSQL  
    🤖 **LLM:** OpenRouter  
    📊 **Мониторинг:** Langfuse  
    🔍 **Валидация:** Multi-agent
    """)

# Основной контент
st.title("🤖 RAG-SQL Agent")
st.markdown("Интеллектуальный агент для анализа SQL баз данных с валидацией и оптимизацией запросов")

# Чат интерфейс
chat_container = st.container()

with chat_container:
    # Отображение истории сообщений
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 Вы:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Ассистент:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
            
            # Если есть SQL запрос, отображаем его отдельно
            if "sql_query" in message:
                st.markdown(f"""
                <div class="sql-query">
                    <strong>🔍 SQL Запрос:</strong><br>
                    {message["sql_query"]}
                </div>
                """, unsafe_allow_html=True)
            
            # Если есть результаты запроса, отображаем их
            if "results" in message and message["results"]:
                display_results(message["results"])

# Функция для отображения результатов
def display_results(results):
    if isinstance(results, list) and len(results) > 0:
        # Преобразуем в DataFrame
        df = pd.DataFrame(results)
        
        st.subheader("📊 Результаты запроса")
        
        # Таблица с данными
        st.dataframe(df, use_container_width=True)
        
        # Визуализация если возможно
        if len(df.columns) >= 2:
            st.subheader("📈 Визуализация")
            
            # Выбор колонок для графика
            col1, col2 = st.columns(2)
            with col1:
                x_axis = st.selectbox("Ось X:", df.columns, key="x_axis")
            with col2:
                y_axis = st.selectbox("Ось Y:", df.columns, key="y_axis")
            
            if x_axis and y_axis:
                try:
                    # Определяем тип графика
                    if df[y_axis].dtype in ['int64', 'float64'] and len(df[x_axis].unique()) < 20:
                        # Столбчатая диаграмма для числовых данных
                        fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} по {x_axis}")
                    elif df[x_axis].dtype in ['int64', 'float64'] and df[y_axis].dtype in ['int64', 'float64']:
                        # Точечная диаграмма для двух числовых колонок
                        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                    else:
                        # Линейный график по умолчанию
                        fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} по {x_axis}")
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Не удалось построить график: {e}")

# Функция для отправки запроса к API
def send_message_to_api(message, session_id):
    try:
        st.write(f"🔄 Отправка запроса к API: {API_URL}")
        
        payload = {
            "text": message,
            "session_id": session_id
        }
        
        response = requests.post(API_URL, json=payload, timeout=30)
        
        st.write(f"📡 Status код: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            st.write(f"✅ Ответ получен: {result}")
            return result
        else:
            st.error(f"❌ Ошибка API: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        st.error(f"🔌 Не удалось подключиться к API: {e}")
        st.error("💡 Убедитесь что backend запущен на http://localhost:8000")
        return None
    except requests.exceptions.Timeout:
        st.error("⏰ Таймаут запроса к API")
        return None
    except Exception as e:
        st.error(f"❌ Неизвестная ошибка: {e}")
        return None

# Поле ввода сообщения
user_input = st.chat_input("Задайте вопрос о данных в базе...")

if user_input:
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Отправляем запрос к API
    with st.spinner("🤔 Анализирую запрос..."):
        response = send_message_to_api(user_input, st.session_state.session_id)
    
    if response:
        # Извлекаем SQL если есть
        sql_query = None
        results = None
        
        # Простая эвристика для извлечения SQL из ответа
        if "SELECT" in response["reply"] or "INSERT" in response["reply"] or "UPDATE" in response["reply"]:
            lines = response["reply"].split('\n')
            for line in lines:
                if line.strip().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE')):
                    sql_query = line.strip()
                    break
        
        # Добавляем ответ ассистента
        assistant_message = {
            "role": "assistant", 
            "content": response["reply"],
            "session_id": response.get("session_id")
        }
        
        if sql_query:
            assistant_message["sql_query"] = sql_query
        
        # Если есть результаты запроса, добавляем их
        # (Здесь можно добавить парсинг результатов из ответа)
        
        st.session_state.messages.append(assistant_message)
        
        # Обновляем session_id если изменился
        if "session_id" in response:
            st.session_state.session_id = response["session_id"]
    
    # Обновляем страницу через экспериментальный метод
    st.experimental_rerun()

# Футер
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🚀 RAG-SQL Agent | PostgreSQL + LangGraph + Streamlit</p>
    <p>⚡ Powered by OpenRouter & Langfuse</p>
</div>
""", unsafe_allow_html=True)
