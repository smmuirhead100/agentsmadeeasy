import json
import os
from typing import AsyncGenerator, List

from anthropic import AsyncAnthropic, types

from ame.core.chat_context import ChatMessage
from ame.core.tools import Tool, ToolCall
from ame.llms.anthropic.utils import chat_messages_to_anthropic_system_and_messages, tool_to_anthropic_tool
from .models import AnthropicLLMModel
from ame.llms.llm import LLM as BaseLLM
from dotenv import load_dotenv

load_dotenv()


class LLM(BaseLLM):
    def __init__(self, model: AnthropicLLMModel = AnthropicLLMModel.CLAUDE_4_5_SONNET) -> None:
        self.model = model
        self.client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    async def astream(
        self,
        messages: list[ChatMessage],
        tools: List[Tool],
    ) -> AsyncGenerator[str | ToolCall]:
        system, messages = chat_messages_to_anthropic_system_and_messages(messages)
        stream = await self.client.messages.create(
            max_tokens=1024,
            system=system,
            messages=messages,
            model=self.model,
            stream=True,
            tools=[tool_to_anthropic_tool(t) for t in tools]
        )

        current_tool_call: ToolCall | None = None
        current_tool_args: str = ""

        async for chunk in stream:
            if isinstance(chunk, types.RawContentBlockStartEvent):
                content_block = chunk.content_block
                if isinstance(content_block, types.ToolUseBlock):
                    current_tool_call = ToolCall(id=content_block.id, name=content_block.name)
                    current_tool_args = ""
            elif isinstance(chunk, types.RawContentBlockDeltaEvent):
                if isinstance(chunk.delta, types.TextDelta):
                    yield chunk.delta.text
                elif isinstance(chunk.delta, types.InputJSONDelta):
                    current_tool_args += chunk.delta.partial_json
            elif isinstance(chunk, types.RawContentBlockStopEvent):
                # Block is done, yield the completed tool call if we have one
                if current_tool_call:
                    if current_tool_args.strip():
                        try:
                            current_tool_call.args = json.loads(current_tool_args)
                        except json.JSONDecodeError:
                            current_tool_call.args = {}
                    else:
                        current_tool_call.args = {}
                    yield current_tool_call
                    current_tool_call = None
                    current_tool_args = ""