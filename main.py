from src.agent import app, AgentState
from langchain_core.messages import HumanMessage, AIMessage
from src.llm_client import langfuse_handler
import uuid # Для генерации ID сессий


def run():
    print("\n")
    print("=== АГЕНТ-КЛАССИФИКАТОР ПРИВЕТСТВУЕТ ВАС ===")
    print("(Введите 'стоп' для выхода)")

   
    conversation_history: AgentState = {
        "messages": [],
        "awaiting_confirmation": False,
        "generated_sql": None,
        "feedback": None,
    }

    while True:

        # Теперь каждый новый цикл — это уникальный ID для Langfuse
        session_id = str(uuid.uuid4())

# 2. Ввод пользователя
        user_input = input("\n👤 Вы: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ["стоп", "exit", "quit"]:
            print("👋 До свидания! Анализ завершен.")
            break
        # 2. Добавляем сообщение в историю
        conversation_history["messages"].append(HumanMessage(content=user_input))

        # 3. Запускаем магию LangGraph
        # Агент сам решит: вызвать инструмент или просто ответить
        try:
            # 4. Запуск графа
            # app.invoke прогонит состояние через все узлы (assistant -> tools -> assistant)
            # Передаем callbacks в конфиг LangGraph
            config = {
                "callbacks": [langfuse_handler],
                "configurable": {"thread_id": session_id}, # Для памяти LangGraph
                "run_name": "Rag_SQL_LLM"              # Название в интерфейсе Langfuse
            }

            # Запускаем граф с конфигом
            final_state = app.invoke(conversation_history, config=config)
            
            # Langfuse автоматически отправляет данные, но если нужно принудительно:
            # langfuse_handler.flush()  # Раскомментировать если будет доступно

            # Обновляем состояние (важно для сохранения контекста диалога)
            conversation_history.update(final_state)

            # 5. Вывод ответа
            # Берем последнее сообщение из истории. 
            # Благодаря циклам в LangGraph, это будет финальный ответ после выполнения всех инструментов.
            last_message = conversation_history["messages"][-1]
            if isinstance(last_message, AIMessage):
                # Если модель выдала пустой контент (только вызовы инструментов), 
                # то в нормальном цикле LangGraph после выполнения инструментов 
                # агент снова вызывается и генерирует текстовое резюме.
                if last_message.content:
                    print(f"\n🤖 Ассистент: {last_message.content}")
                else:
                    # Это на случай, если цепочка прервалась на вызове инструмента
                    print("\n🤖 Ассистент: Запрос обрабатывается...")
            
        except Exception as e:
            print(f"!!! Ошибка в логике агента: {e}")
