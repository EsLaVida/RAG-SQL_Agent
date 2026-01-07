from langchain_openai import ChatOpenAI
from config.settings import OPENAI_API_KEY


#есть более умная модель mistralai/devstral-2512:free
# можно попробовать более мощную модель: google/gemini-2.5-flash
#Mistral требует жесткой последовательности ролей (user, assistant, user, assistant...), попробуем другую модель
llm = ChatOpenAI(
    model="xiaomi/mimo-v2-flash:free",
    base_url="https://openrouter.ai/api/v1",
    temperature=0.4,
    api_key=OPENAI_API_KEY
)

