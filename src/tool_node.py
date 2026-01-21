from langchain_core.messages import ToolMessage


class CustomToolNode:
    def __init__(self, tools: list):
        # Сохраняем инструменты в словарь для быстрого доступа по имени
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, state: dict):
        """Этот метод делает класс 'вызываемым', как функцию"""
        messages = state.get("messages", [])
        last_message = messages[-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        tool_outputs = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            arguments = tool_call["args"]
            
            # Логика поиска и запуска
            tool = self.tools_by_name.get(tool_name)
            if tool:
                try:
                    # Здесь будет точка входа для Langfuse в будущем
                    result = tool.invoke(arguments)
                except Exception as e:
                    result = f"Error in {tool_name}: {str(e)}"
            else:
                result = f"Tool {tool_name} not found."

            tool_outputs.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
            )
        
        return {"messages": tool_outputs}