import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def run_init():
    conn = None
    try:
        # 1. Сначала подключаемся к СИСТЕМНОЙ базе 'postgres'
        print("🔗 Подключение к системной базе для создания структуры...")
        conn = psycopg2.connect(
            dbname="postgres",  # Подключаемся к той, что точно есть
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        target_db = os.getenv("DB_NAME", "company_data")
        
        # Проверяем, существует ли база
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{target_db}'")
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f"CREATE DATABASE {target_db}")
            print(f"✨ База данных '{target_db}' создана.")
        else:
            print(f"✅ База данных '{target_db}' уже существует.")
            
        cur.close()
        conn.close()

        # 2. Теперь подключаемся к нашей новой базе
        print(f"📡 Подключение к '{target_db}' для создания таблиц...")
        conn = psycopg2.connect(
            dbname=target_db,
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()
        
        # Читаем SQL файл
        with open('init_db.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        cur.execute(sql_script)
        conn.commit()
        print("🚀 Таблицы созданы и данные загружены!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_init()