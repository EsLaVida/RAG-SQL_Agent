from langchain_openai import ChatOpenAI
from config.settings import OPENAI_API_KEY
from langfuse.langchain import CallbackHandler
import os
from dotenv import load_dotenv
from langfuse import Langfuse
# Загружаем переменные из .env файла
load_dotenv()

langfuse_handler = CallbackHandler()

#Создадим класс для нашей LLM для мониторинга его через репозиторий langfuse
class LLMManager:
    """
    Класс для управления моделями. 
    Позволяет централизованно менять настройки для всех агентов.
    """
    def __init__(self, model_id: str, temperature: float = 0.0):
        self.model_id = model_id
        self.temperature = temperature
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = OPENAI_API_KEY  # Загружаем ОДИН РАЗ

    def create_client(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.model_id,
            temperature=self.temperature,
            api_key=OPENAI_API_KEY,
            base_url=self.base_url,
            # Теперь каждый созданный клиент автоматически шлет логи в Langfuse
            callbacks=[langfuse_handler] # Подключаем мониторинг
        )

# Наш АГЕНТ (Оркестратор)
# MiMo-v2: Быстрый, дешевый, отлично справляется с маршрутизацией
llm = LLMManager(
    model_id="xiaomi/mimo-v2-flash:free", 
    temperature=0.4
).create_client()

# Наш ИНСПЕКТОР (Валидатор и Оптимизатор)
# Devstral: Специализированная модель для кода, идеальна для SQL-верификации
llm_inspector = LLMManager(
    model_id="mistralai/devstral-2512:free", 
    temperature=0.0
).create_client()