#создадим свою базу данных для тестирования агента

import sqlite3

def init_db():
    conn = sqlite3.connect('company.db')
    cursor = conn.cursor()

    # 1. Создаем таблицы
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            budget REAL
        );

        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            salary REAL,
            dept_id INTEGER,
            FOREIGN KEY (dept_id) REFERENCES departments (id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            deadline DATE,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS employee_projects (
            employee_id INTEGER,
            project_id INTEGER,
            PRIMARY KEY (employee_id, project_id),
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            FOREIGN KEY (project_id) REFERENCES projects (id)
        );
    ''')

    # 2. Наполняем данными
    depts = [
        (1, 'IT-департамент', 1000000), 
        (2, 'Отдел продаж', 500000), 
        (3, 'HR-отдел', 300000)
    ]
    cursor.executemany('INSERT OR IGNORE INTO departments VALUES (?,?,?)', depts)

    emps = [
        (1, 'Алексей', 'Lead Developer', 350000, 1),
        (2, 'Мария', 'Senior Dev', 250000, 1),
        (3, 'Иван', 'Sales Manager', 150000, 2),
        (4, 'Елена', 'HR Specialist', 120000, 3),
        (5, 'Дмитрий', 'Junior Dev', 90000, 1),
        (6, 'Анна', 'Account Manager', 140000, 2)
    ]
    cursor.executemany('INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?)', emps)

    projs = [
        (1, 'Внедрение ИИ', '2025-12-01', 'В процессе'),
        (2, 'Облачная миграция', '2025-10-15', 'Завершен'),
        (3, 'Новая CRM-система', '2026-03-20', 'Планирование')
    ]
    cursor.executemany('INSERT OR IGNORE INTO projects VALUES (?,?,?,?)', projs)

    # Связи сотрудников и проектов
    relations = [
        (1, 1), (2, 1), (5, 1), # Программисты на ИИ
        (1, 2), (2, 2),          # Lead и Senior на миграции
        (3, 3), (6, 3)           # Продажники на CRM
    ]
    cursor.executemany('INSERT OR IGNORE INTO employee_projects VALUES (?,?)', relations)

    conn.commit()
    conn.close()
    print("✅ База данных company.db успешно создана с русскоязычными данными!")

if __name__ == "__main__":
    init_db()