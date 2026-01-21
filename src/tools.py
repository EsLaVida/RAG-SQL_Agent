import sqlite3
from langchain_core.tools import tool
from src.tool_node import CustomToolNode

DB_PATH = "company.db"

@tool
def user_confirmation(query: str) -> bool:
    """
    Подтверждает, что пользователь согласен на выполнение конкретного SQL-запроса.
    Этот инструмент следует вызывать ТОЛЬКО тогда, когда пользователь явно ответил 'Да' 
    или 'Выполняй' на предложенный текст запроса.
    """
    return True

@tool
def get_db_schema():
    """
    Возвращает схему базы данных (список таблиц и колонок). 
    Используй этот инструмент перед написанием SQL-запроса, чтобы знать точные названия таблиц и полей.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_info = []
    for table_name in tables:
        t_name = table_name[0]
        # Пропускаем системные таблицы sqlite
        if t_name.startswith('sqlite_'): continue
            
        cursor.execute(f"PRAGMA table_info({t_name});")
        columns = cursor.fetchall()
        col_desc = ", ".join([f"{col[1]} ({col[2]})" for col in columns])
        schema_info.append(f"Таблица: {t_name}\nКолонки: {col_desc}")
    
    conn.close()
    return "\n\n".join(schema_info)

@tool
def execute_sql(query: str):
    """
    Выполняет SQL-запрос к базе данных и возвращает результат.
    Принимает только SELECT запросы.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Безопасность: разрешаем только чтение
        if not query.strip().lower().startswith("select"):
            return "Ошибка: Разрешены только запросы SELECT."
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Получаем названия колонок для ответа
        column_names = [description[0] for description in cursor.description]
        conn.close()
        
        if not rows:
            return "Запрос выполнен, но данных не найдено."
            
        # Форматируем результат в список словарей
        return [dict(zip(column_names, row)) for row in rows]
        
    except Exception as e:
        return f"Ошибка SQL: {str(e)}"

tools_list = [get_db_schema, execute_sql, user_confirmation]

tool_node = CustomToolNode(tools=tools_list)
