from src.agent import app, AgentState
from langchain_core.messages import HumanMessage, AIMessage
from src.llm_client import langfuse_handler
import uuid # Для генерации ID сессий


from fastapi import FastAPI
from pydantic import BaseModel
from src.agent import app as langgraph_app
from langchain_core.messages import HumanMessage
import uuid
app = FastAPI(title="RAG SQL Agent API")


# --- ЛОГИКА API (FastAPI) ---
# Модель данных для запроса
class UserMessage(BaseModel):
    text: str
    session_id: str = None # Можно передавать существующий ID сессии

@app.post("/chat")
async def chat_endpoint(payload: UserMessage):
    # Если session_id не передан, создаем новый (для нового чата)
    thread_id = payload.session_id or str(uuid.uuid4())
    
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [langfuse_handler],
        "run_name": "API_SQL_Agent"
    }

    # ВАЖНО: Благодаря checkpointer в Postgres, мы передаем ТОЛЬКО новое сообщение.
    # Старые сообщения LangGraph сам подтянет из базы по thread_id.
    inputs = {"messages": [HumanMessage(content=payload.text)]}
    
    final_state = langgraph_app.invoke(inputs, config=config)
    
    last_message = final_state["messages"][-1]
    return {
        "reply": last_message.content if last_message.content else "Инструменты выполнены",
        "session_id": thread_id
    }


# --- ЛОГИКА CLI (Для тестов в консоли) ---

def run_cli():
    print("\n=== АГЕНТ-КЛАССИФИКАТОР ПРИВЕТСТВУЕТ ВАС ===")
    print("(Введите 'стоп' для выхода)")

    # session_id создаем ОДИН РАЗ перед циклом, чтобы агент помнил контекст
    session_id = str(uuid.uuid4())
    print(f"🆔 ID твоей сессии: {session_id}")

    while True:
        user_input = input("\n👤 Вы: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ["стоп", "exit", "quit"]:
            print("👋 До свидания!")
            break

        try:
            config = {
                "callbacks": [langfuse_handler],
                "configurable": {"thread_id": session_id},
                "run_name": "CLI_SQL_Agent"
            }

            # Передаем только новое сообщение
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            # invoke прогонит стейт через граф. Чекпоинтер сам сохранит всё в Postgres.
            final_state = langgraph_app.invoke(inputs, config=config)

            last_message = final_state["messages"][-1]
            
            if isinstance(last_message, AIMessage) and last_message.content:
                print(f"\n🤖 Ассистент: {last_message.content}")
            else:
                print("\n🤖 Ассистент: (Выполнены инструменты, жду следующего шага)")
            
        except Exception as e:
            print(f"!!! Ошибка: {e}")

if __name__ == "__main__":
    # Если запускаем просто файл, включается консольный режим
    run_cli()

# Функция для запуска FastAPI
def run():
    """Запуск FastAPI сервера"""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
