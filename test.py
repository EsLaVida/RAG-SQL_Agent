import psycopg
try:
    conn = psycopg.connect("postgresql://postgres:postgres@127.0.0.1:5432/company_data")
    print("✅ Связь с базой установлена успешно!")
    conn.close()
except Exception as e:
    print(f"❌ Ошибка связи: {e}")