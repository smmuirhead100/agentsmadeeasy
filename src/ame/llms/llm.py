from abc import ABC, abstractmethod
from typing import AsyncGenerator, List

from ame.core.chat_context import ChatMessage
from ame.core.tools import Tool, ToolCall


class LLM(ABC):
    @abstractmethod
    async def astream(
        self,
        messages: list[ChatMessage],
        tools: List[Tool],
    ) -> AsyncGenerator[str | ToolCall]:
        ...