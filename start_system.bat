@echo off
echo 🚀 Запуск RAG-SQL Agent...
echo.

echo 📋 Проверяем зависимости...
python -c "import streamlit, requests, plotly, pandas" 2>nul
if errorlevel 1 (
    echo ❌ Ошибка: Не все зависимости установлены
    echo 💡 Выполните: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Зависимости в порядке

echo.
echo 🌐 Запуск Backend (FastAPI)...
start "Backend" cmd /k "python app.py"

timeout /t 3 >nul

echo 🎨 Запуск Frontend (Streamlit)...
start "Frontend" cmd /k "streamlit run streamlit_app.py"

echo.
echo ✅ Система запущена!
echo 🌐 Backend: http://localhost:8000
echo 🎨 Frontend: http://localhost:8501
echo 📊 Langfuse: http://localhost:3000 (если настроен)
echo.
echo 💡 Закройте это окно для остановки всех сервисов
pause
