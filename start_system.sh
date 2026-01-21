#!/bin/bash

echo "🚀 Запуск RAG-SQL Agent..."
echo

# Проверяем зависимости
echo "📋 Проверяем зависимости..."
python3 -c "import streamlit, requests, plotly, pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Ошибка: Не все зависимости установлены"
    echo "💡 Выполните: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Зависимости в порядке"
echo

# Запуск Backend
echo "🌐 Запуск Backend (FastAPI)..."
python3 app.py &
BACKEND_PID=$!

# Ждем запуска backend
sleep 3

# Запуск Frontend  
echo "🎨 Запуск Frontend (Streamlit)..."
streamlit run streamlit_app.py &
FRONTEND_PID=$!

echo
echo "✅ Система запущена!"
echo "🌐 Backend: http://localhost:8000"
echo "🎨 Frontend: http://localhost:8501"
echo "📊 Langfuse: http://localhost:3000 (если настроен)"
echo
echo "💡 Нажмите Ctrl+C для остановки всех сервисов"

# Ожидаем Ctrl+C
trap "echo '🛑 Остановка сервисов...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
