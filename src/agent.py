from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional, Annotated, Sequence
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, AIMessage
from src.tools import tool_node, get_db_schema, execute_sql, user_confirmation #наши инструменты
from src.llm_client import llm
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from config.prompts import sys_msg



class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Храним сам SQL запрос, который агент придумал, 
    # чтобы показать его пользователю для подтверждения
    generated_sql: Optional[str]
    # Флаг: ждем ли мы от пользователя "да/нет" для выполнения этого SQL
    awaiting_confirmation: bool
  

def assistant(state: AgentState) -> AgentState:

# 1. Инициализация состояний (State)
    # Используем .get() или setdefault, чтобы избежать ошибок при первом запуске
    state.setdefault("generated_sql", None)
    state.setdefault("awaiting_confirmation", False)

    messages = state["messages"]

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

# 3. ДИНАМИЧЕСКИЙ BIND (Guardrails)
    # Набор для этапа "подготовки" (не даем доступ к базе напрямую)
    prep_tools = [get_db_schema, user_confirmation]
    
    # Полный набор (включая выполнение SQL)
    # Мы даем его ТОЛЬКО если подтверждение уже получено
    full_tools = [get_db_schema, execute_sql, user_confirmation]

# Если подтверждение УЖЕ есть в истории сообщений
    if is_confirmed:
        # Даем полный доступ, чтобы агент мог выполнить запрос и ответить
        llm_with_tools = llm.bind_tools([get_db_schema, execute_sql, user_confirmation])
        state["awaiting_confirmation"] = False
    
    # Если SQL уже предложен, но подтверждения в ToolMessage еще нет
    elif state.get("generated_sql"):
        # ВАЖНО: Даем и подтверждение, и выполнение. 
        # Модель сама решит: сначала вызвать подтверждение, а потом (на след. шаге) выполнение.
        llm_with_tools = llm.bind_tools([user_confirmation, execute_sql])
        state["awaiting_confirmation"] = True
    
    # Если мы только начали
    else:
        llm_with_tools = llm.bind_tools([get_db_schema, user_confirmation])
        state["awaiting_confirmation"] = False


# 4. Вызов модели
    ai_msg = llm_with_tools.invoke([sys_msg] + messages)

# 5. Обновление стейта на основе действий модели

    # Если модель вызвала подтверждение — фиксируем SQL и переходим в режим ожидания
    if ai_msg.tool_calls:
        for call in ai_msg.tool_calls:
            if call['name'] == 'user_confirmation':
                state["generated_sql"] = call['args'].get('query')
                state["awaiting_confirmation"] = True
            
            # Если вызвано выполнение SQL — значит режим ожидания можно выключать
            if call['name'] == 'execute_sql':
                state["awaiting_confirmation"] = False

    # Синхронизируем состояние подтверждения (is_confirmed мы рассчитали в пункте 2)
    # Если подтверждение получено, сбрасываем флаг ожидания
    if is_confirmed:
        state["awaiting_confirmation"] = False

    return {
        "messages": [ai_msg], 
        "generated_sql": state.get("generated_sql"),
        "awaiting_confirmation": state["awaiting_confirmation"]
    }


#графы
# 1. Инициализация графа
graph = StateGraph(AgentState)
# 2. Добавляем узлы
graph.add_node("agent", assistant)
graph.add_node("tools", tool_node)
# 4. Настраиваем логику переходов
graph.set_entry_point("agent")
def route(state: AgentState) -> str:
    last = state["messages"][-1]
    # Если модель хочет вызвать инструмент — идем в узел tools
    if isinstance(last, AIMessage) and hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    # Если инструментов нет — завершаем работу (ждем ответа пользователя)
    return END

# Добавляем условные переходы
graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
# После выполнения любого инструмента возвращаемся к агенту, 
# чтобы он проанализировал результат (схему или данные из БД)
graph.add_edge("tools", "agent")
# 4. Компиляция
app = graph.compile()