import sqlite3
from langchain_core.tools import tool
from src.tool_node import CustomToolNode

import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_pg_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )

DB_PATH = "init_db.sql"

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
    Возвращает схему базы данных PostgreSQL (список таблиц и колонок). 
    Используй этот инструмент перед написанием SQL-запроса.
    """
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        # SQL для получения всех таблиц и их колонок в схеме 'public'
        query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            return "База данных пуста или таблицы находятся не в схеме 'public'."

        schema_dict = {}
        for table, column, dtype in rows:
            if table not in schema_dict:
                schema_dict[table] = []
            schema_dict[table].append(f"{column} ({dtype})")
        
        schema_info = []
        for table, columns in schema_dict.items():
            schema_info.append(f"Таблица: {table}\nКолонки: {', '.join(columns)} ")
        
        cursor.close()
        conn.close()
        return "\n\n".join(schema_info)
    except Exception as e:
        return f"Ошибка при получении схемы: {str(e)}"

@tool
def execute_sql(query: str):
    """
    Выполняет SQL-запрос к PostgreSQL и возвращает результат.
    Принимает только SELECT запросы.
    """
    try:
        conn = get_pg_connection()
        # RealDictCursor автоматически делает zip(names, row) за нас
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Очистка запроса от лишних символов (Markdown и т.д.)
        clean_query = query.strip().replace("```sql", "").replace("```", "").strip()
        
        if not clean_query.lower().startswith("select"):
            return "Ошибка: Разрешены только запросы SELECT."
            
        cursor.execute(clean_query)
        rows = cursor.fetchall()
        
        # Сохраняем результат в RAG кэш
        if rows and clean_query.strip().upper().startswith('SELECT'):
            result_text = str(rows)[:200]  # Ограничиваем размер
            store_query_result(f"SQL запрос", clean_query, result_text)
        
        cursor.close()
        conn.close()
        
        if not rows:
            return "Запрос выполнен успешно, но данных не найдено."
            
        return rows # Возвращает список словарей [{col: val}, ...]
        
    except Exception as e:
        return f"Ошибка SQL PostgreSQL: {str(e)}"


@tool
def search_company_knowledge(query: str):
    """
    Ищет ответы в неструктурированных документах компании: 
    политики, инструкции, регламенты, описания процессов.
    Используй это, если вопрос НЕ касается конкретных цифр из базы данных.
    """
    try:
        from src.vector_store import vector_db
        results = vector_db.search(query)
        if not results:
            return "В базе знаний документов по этому вопросу не найдено."
        
        context = "\n".join([f"- {res['text']}" for res in results])
        return f"Информация из базы знаний:\n{context}"
    except Exception as e:
        return f"Ошибка векторного поиска: {e}"


tools_list = [get_db_schema, execute_sql, user_confirmation, search_company_knowledge]

tool_node = CustomToolNode(tools=tools_list)
