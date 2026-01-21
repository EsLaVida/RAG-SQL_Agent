from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional, Annotated, Sequence
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, AIMessage, SystemMessage
from src.tools import tool_node, get_db_schema, execute_sql, user_confirmation, search_company_knowledge #наши инструменты
from src.llm_client import llm, llm_inspector
from langgraph.graph.message import add_messages
from config.prompts import sys_msg, validator_sys_msg, optimizer_sys_msg # Промпты для LLM
from config.few_shot_example import ASSISTANT_FEW_SHOT, VALIDATOR_FEW_SHOT, OPTIMIZER_FEW_SHOT  # ПримерыFew-Shot для LLM

import os
from dotenv import load_dotenv



class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Храним сам SQL запрос, который агент придумал, 
    # чтобы показать его пользователю для подтверждения
    generated_sql: Optional[str]
    # Флаг: ждем ли мы от пользователя "да/нет" для выполнения этого SQL
    awaiting_confirmation: bool
    # Храним фидбек от наших функций поиска синтаксической ошибки/ оптимизации
    feedback: Optional[str] 

def assistant(state: AgentState) -> AgentState:

    # 1. Инициализация состояний (State)
    # Используем .get() или setdefault, чтобы избежать ошибок при первом запуске
    state.setdefault("generated_sql", None)
    state.setdefault("awaiting_confirmation", False)
    messages = state["messages"]
    state.setdefault("feedback", None) # Новое поле для "мыслей" валидатора/оптимизатора

    # 2. Проверяем, было ли получено подтверждение от пользователя
    # Смотрим последний ответ от инструмента user_confirmation
    is_confirmed = False
    for msg in reversed(messages):
        # Ищем сообщение от нашего инструмента подтверждения
        if isinstance(msg, ToolMessage) and msg.name == 'user_confirmation':
            # Если инструмент вернул True (или строку "True"), значит этап пройден
            if msg.content == "True" or msg.content is True:
                is_confirmed = True
            break
        if isinstance(msg, HumanMessage):
            break

    # 3. ФОРМИРОВАНИЕ СИСТЕМНОГО ПРОМПТА (Production Logic)
    current_sys_msg = sys_msg.content

    # Если валидатор или оптимизатор записали что-то в feedback, добавляем это как 
    # приоритетную инструкцию, которую не видит пользователь в чате.
    internal_feedback = state.get("feedback")
    if internal_feedback:
        current_sys_msg += f"\n\n[ВНУТРЕННЯЯ КРИТИКА СИСТЕМЫ]: {internal_feedback}. Исправь запрос немедленно."

    # Сохраняем поддержку старой логики ошибок (на всякий случай)
    if messages and isinstance(messages[-1].content, str) and "SQL Error" in messages[-1].content:
        current_sys_msg += f"\nОШИБКА В ЗАПРОСЕ: {messages[-1].content}."

    if state.get("generated_sql") and not is_confirmed:
        current_sys_msg += f"\nТЕКУЩИЙ ПОДГОТОВЛЕННЫЙ SQL: {state['generated_sql']}. Если пользователь подтвердит, используй user_confirmation."

    final_sys_msg = SystemMessage(content=current_sys_msg)

    # Настройка инструментов в зависимости от стадии
    if is_confirmed:
        llm_with_tools = llm.bind_tools([get_db_schema, execute_sql, user_confirmation, search_company_knowledge])
    elif state.get("generated_sql"):
        # Если SQL есть, агент может либо подтвердить его, либо переделать, если он ему не нравится
        llm_with_tools = llm.bind_tools([search_company_knowledge, user_confirmation, execute_sql])
    else:
        # Добавляем RAG для улучшения запросов
        llm_with_tools = llm.bind_tools([get_db_schema, search_company_knowledge, user_confirmation])

    # 4. Вызов модели
    #upd (теперь список состоит только из объектов сообщений)
    # Нормализуем историю для Mistral/OpenRouter (чтобы не было двух Human подряд 
    # или ToolMessage сразу после HumanMessage)
    normalized_messages = []
    for msg in messages:
        # Если в истории два сообщения от человека подряд — Mistral выдаст ошибку.
        # Мы оставляем только последнее (самое актуальное).
        if normalized_messages and normalized_messages[-1].type == msg.type == 'human':
            normalized_messages[-1] = msg
        else:
            normalized_messages.append(msg)

    # Если последнее сообщение от человека (наше "да"), а до него был вызов инструмента,
    # некоторые провайдеры требуют, чтобы между ними был ответ от AI.
    # Но в LangGraph обычно достаточно просто передать список корректно:

    ai_msg = llm_with_tools.invoke([final_sys_msg] + normalized_messages)

    # 5. Обновление стейта на основе действий модели
    # Если модель вызвала подтверждение — фиксируем SQL и переходим в режим ожидания
    if ai_msg.tool_calls:
        for call in ai_msg.tool_calls:
            # Если модель вызывает подтверждение:
            if call['name'] == 'user_confirmation':
                # ВАЖНО: Сейчас мы записываем "черновик" SQL. 
                # Функция route() перехватит этот вызов и отправит его по цепочке:
                # Validator (проверка) -> Optimizer (улучшение).
                # Финальный SQL в state["generated_sql"] попадет только после них.
                state["generated_sql"] = call['args'].get('query')
                # Включаем "предохранитель": пока цепочка LLM не закончит работу,
                # и пользователь не нажмет "Да", выполнение в базу закрыто.
                state["awaiting_confirmation"] = True
            # Если вызвано выполнение SQL:
            if call['name'] == 'execute_sql':
                # Запрос ушел в БД, сбрасываем режим ожидания.
                state["awaiting_confirmation"] = False
    else:
        # Если модель просто ответила текстом (без инструментов), 
        # Сбрасываем ожидание, так как активного процесса генерации SQL сейчас нет.
        state["awaiting_confirmation"] = False
    # Синхронизируем состояние на основе ответа пользователя
    if is_confirmed:
        # Если в истории сообщений найден ToolMessage от user_confirmation со значением True:
        # 1. Сбрасываем флаг ожидания, так как пользователь "дал добро".
        # 2. Это открывает агенту путь к вызову инструмента execute_sql на следующем шаге.
        state["awaiting_confirmation"] = False
    # ВАЖНО: возвращаем feedback: None, чтобы очистить его после того, как агент его прочитал
    return {
        "messages": [ai_msg], 
        "generated_sql": state.get("generated_sql"),
        "awaiting_confirmation": state["awaiting_confirmation"],
        "feedback": None
    }

#добавим к основному агенту еще два узла для проверки синтаксиса SQL(validation) и его улучшения(optimization)

# --- Узел Валидатора (Production) ---
def sql_valiadator_node(state: AgentState) -> AgentState:
    query = state.get("generated_sql")
    if not query: return state
    
    # Мы используем заранее подготовленный validator_sys_msg из файла prompts.py
    # Он уже содержит роль, Few-Shot примеры и инструкцию.   
    response = llm_inspector.invoke([
        SystemMessage(content=validator_sys_msg),
        HumanMessage(content=f"Проверь этот SQL: {query}")
    ])
    #Убираем лишние пробелы и переносы (.strip())
    verdict = response.content.strip()

    if "OK" not in verdict.upper():
        print(f"🛡️ [DEVSTRAL VALIDATOR]: Обнаружена проблема! {verdict}")
        # Записываем критику в feedback, чтобы Ассистент её увидел
        return {"feedback": f"Ошибка синтаксиса/безопасности: {verdict}"}
    print(f"🛡️ [DEVSTRAL VALIDATOR]: ✅ SQL проверен, ошибок не обнаружено.")
    return {"feedback": None} # Очищаем feedback, если всё хорошо


# --- Узел Оптимизатора (Production) ---
def sql_opimizer_node(state: AgentState) -> AgentState:
    query = state.get("generated_sql")
    if not query: return state
    
    response = llm_inspector.invoke([
        SystemMessage(content=optimizer_sys_msg),
        HumanMessage(content=f"Оптимизируй этот SQL: {query}")
    ])

    verdict = response.content.strip()
    
    if "OK" not in verdict.upper():
        print(f"🚀 [DEVSTRAL OPTIMIZER]: Дал рекомендацию. {verdict}")
        return {"feedback": f"Рекомендация по логике: {verdict}"}
    print(f"🚀 [DEVSTRAL OPTIMIZER]: ✅ Запрос уже оптимален.")
    return state
    
#графы
# 1. Инициализация графа
graph = StateGraph(AgentState)
# 2. Добавляем узлы
#UPD дообавляем узлы валидации и оптимизации SQL
graph.add_node("validator", sql_valiadator_node)
graph.add_node("optimizer", sql_opimizer_node)
graph.add_node("agent", assistant)
graph.add_node("tools", tool_node)
# 4. Настраиваем логику переходов

graph.set_entry_point("agent")

#UPD Перестраиваем логику переходов
def route(state: AgentState) -> str:
    last = state["messages"][-1]
    
    # Если инструментов нет — завершаем (ждем ввода пользователя в чат)
    if not (isinstance(last, AIMessage) and last.tool_calls):
        return END

    # Если инструменты есть, проверяем какие именно
    for call in last.tool_calls:
        if call['name'] == 'user_confirmation':
            # Если агент хочет подтвердить SQL, отправляем в цепочку проверок
            return "validator"
    
    # Если это любые другие инструменты (например, get_db_schema), идем в обычный tool_node
    return "tools"

# Добавляем условные переходы
#UPD Настроиваем цепочку: Validator -> Optimizer -> Tools (Confirmation)
graph.add_conditional_edges("agent", route, {
    "validator": "validator", 
    "tools": "tools", 
    END: END
    })
# После выполнения любого инструмента возвращаемся к агенту, 
# чтобы он проанализировал результат (схему или данные из БД)
graph.add_edge("validator", "optimizer")
graph.add_edge("optimizer", "tools") # Отправляем уже чистый и быстрый SQL в инструменты
graph.add_edge("tools", "agent")


# 4. Компиляция
load_dotenv()

# Используем Memory checkpointer - он стабильно работает
# PostgreSQL checkpointer требует совместимости версий
from langgraph.checkpoint.memory import MemorySaver
memory_checkpointer = MemorySaver()

app = graph.compile(checkpointer=memory_checkpointer)