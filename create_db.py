#создадим более сложную базу данных для тестирования агента

import sqlite3
import random
from datetime import datetime, timedelta

def create_rich_db():
    conn = sqlite3.connect('company.db')
    cursor = conn.cursor()

    # 1. Департаменты
    cursor.execute('''CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, budget REAL)''')
    deps = [('IT', 500000), ('Sales', 300000), ('HR', 150000), ('Marketing', 250000), ('Data Science', 450000)]
    cursor.executemany('INSERT INTO departments (name, budget) VALUES (?, ?)', deps)

    # 2. Сотрудники
    cursor.execute('''CREATE TABLE employees (
        id INTEGER PRIMARY KEY, 
        name TEXT, 
        dep_id INTEGER, 
        hire_date TEXT, 
        role TEXT,
        FOREIGN KEY(dep_id) REFERENCES departments(id))''')
    
    roles = ['Junior', 'Middle', 'Senior', 'Lead', 'Manager']
    names = ['Alex', 'Maria', 'Ivan', 'Elena', 'Petr', 'Anna', 'Dmitry', 'Olga', 'Sergey', 'Svetlana']
    
    for i in range(1, 51): # Создаем 50 сотрудников
        cursor.execute('INSERT INTO employees (name, dep_id, hire_date, role) VALUES (?, ?, ?, ?)',
                       (random.choice(names) + f"_{i}", random.randint(1, 5), '2023-01-01', random.choice(roles)))

    # 3. Зарплаты (с историей)
    cursor.execute('''CREATE TABLE salaries (
        emp_id INTEGER, 
        amount REAL, 
        updated_at TEXT, 
        FOREIGN KEY(emp_id) REFERENCES employees(id))''')
    
    for i in range(1, 51):
        cursor.execute('INSERT INTO salaries VALUES (?, ?, ?)', (i, random.randint(40000, 150000), '2024-01-01'))

    # 4. Проекты и участие
    cursor.execute('''CREATE TABLE projects (id INTEGER PRIMARY KEY, title TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE project_assignments (emp_id INTEGER, project_id INTEGER, hours_spent INTEGER)''')
    
    projs = [('AI Chatbot', 'Active'), ('Mobile App', 'Planning'), ('Data Migration', 'Completed'), ('Cloud Setup', 'Active')]
    cursor.executemany('INSERT INTO projects (title, status) VALUES (?, ?)', projs)
    
    for i in range(1, 40): # Часть сотрудников занята в проектах
        cursor.execute('INSERT INTO project_assignments VALUES (?, ?, ?)', (i, random.randint(1, 4), random.randint(10, 100)))

    conn.commit()
    conn.close()
    print("🚀 База 'company.db' создана с 50+ записями и сложными связями!")

create_rich_db()