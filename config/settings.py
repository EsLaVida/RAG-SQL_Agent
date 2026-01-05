# config/settings.py
from dotenv import load_dotenv
import os

# Загружаем переменные из .env файла
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Не найден OPENAI_API_KEY в файле .env")
