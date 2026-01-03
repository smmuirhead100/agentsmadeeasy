from abc import ABC, abstractmethod
from typing import AsyncGenerator, List

from agents.core.chat_context import ChatMessage
from agents.core.tools import Tool, ToolCall


class LLM(ABC):
    @abstractmethod
    async def astream(
        self,
        messages: list[ChatMessage],
        tools: List[Tool],
    ) -> AsyncGenerator[str | ToolCall]:
        ...