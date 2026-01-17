from typing import AsyncGenerator, List, Optional
import asyncio
import inspect

from pydantic import BaseModel, create_model
from ame.core.chat_context import ChatMessage, ChatRole
from ame.core.tools import Tool, ToolCall
from ame.llms.llm import LLM

_IS_TOOL = "is_tool"


class AgentWithToolsConfig(BaseModel):
    max_message_history: int = 50


class AgentWithTools:
    def __init__(self, llm: LLM, instructions: str, config: AgentWithToolsConfig = AgentWithToolsConfig()) -> None:
        self._llm = llm
        self._messages: List[ChatMessage] = [ChatMessage(role=ChatRole.SYSTEM, content=instructions)]
        self._config = config
        self._tools = self._get_tools_from_decorated_methods()
        self._thinking = False

    async def astream(self, chat_message: Optional[ChatMessage] = None) -> AsyncGenerator[str | ToolCall]:
        self._thinking = True

        if chat_message:
            self._messages.append(chat_message)
            if len(self._messages) > self._config.max_message_history:
                # Always preserve the system message (first message) when trimming
                system_message = next((m for m in self._messages if m.role == ChatRole.SYSTEM), None)
                non_system_messages = [m for m in self._messages if m.role != ChatRole.SYSTEM]
                # Keep system message + last (max_message_history - 1) non-system messages
                self._messages = ([system_message] if system_message else []) + non_system_messages[-(self._config.max_message_history - 1):]

        response = ""
        tool_calls: List[ToolCall] = []

        stream = self._llm.astream(messages=self._messages, tools=self._tools)
        async for chunk in stream:
            if isinstance(chunk, ToolCall):
                tool_calls.append(chunk)
            else:
                response += chunk
                yield chunk

        if response:
            self._messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=response))

        if tool_calls:
            tc_responses = await asyncio.gather(*[self._execute_tool_call(tool_call=tc) for tc in tool_calls])
            for tool_call, tc_response in zip(tool_calls, tc_responses):
                tool_call.response = tc_response
                yield tool_call
            tool_calls_message = ChatMessage(role=ChatRole.ASSISTANT, content=tool_calls)

            async for chunk_after_tool_calls in self.astream(tool_calls_message):
                yield chunk_after_tool_calls
        self._thinking = False

    def update_instructions(self, instructions: str) -> None:
        system_message = next(m for m in self._messages if m.role == ChatRole.SYSTEM)
        system_message.content = instructions

    async def _execute_tool_call(self, tool_call: ToolCall) -> str:
        method_name = tool_call.name
        method = getattr(self, method_name)
        if not method:
            raise ValueError(f"Method '{method_name}' not found on {self.__class__.__name__}")

        args = tool_call.args if tool_call.args is not None else {}
        result = await method(**args)
        return str(result)

    def _get_tools_from_decorated_methods(self) -> List[Tool]:
        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, _IS_TOOL):
                sig = inspect.signature(attr)
                fields = {name: (param.annotation, ...) for name, param in sig.parameters.items() if name != "self"}
                input_schema = create_model(f"{attr.__name__}Input", **fields) if fields else create_model(f"{attr.__name__}Input")
                tools.append(Tool(
                    name=attr.__name__,
                    description=attr.__doc__ or "",
                    input_schema=input_schema,
                ))
        return tools