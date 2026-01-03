import os
from typing import AsyncGenerator, List

from google import genai
from google.genai import types

from ame.core.chat_context import ChatMessage
from ame.core.tools import Tool, ToolCall
from ame.llms.gemini.utils import chat_messages_to_gemini_system_and_contents, tool_to_gemini_function_declaration
from .models import GeminiLLMModel
from ame.llms.llm import LLM as BaseLLM
from dotenv import load_dotenv

load_dotenv()


class LLM(BaseLLM):
    def __init__(self, model: GeminiLLMModel = GeminiLLMModel.GEMINI_2_5_FLASH) -> None:
        self.model = model.value
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)

    async def astream(
        self,
        messages: list[ChatMessage],
        tools: List[Tool],
    ) -> AsyncGenerator[str | ToolCall]:
        system_prompt, contents = chat_messages_to_gemini_system_and_contents(messages)

        # Prepare tools configuration
        function_declarations = [tool_to_gemini_function_declaration(t) for t in tools]
        gemini_tools = types.Tool(function_declarations=function_declarations) if function_declarations else None

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[gemini_tools] if gemini_tools else None,
            temperature=1.0,
        )

        # Use async streaming
        stream = await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )

        current_tool_calls = []
        has_text_content = False

        async for chunk in stream:
            # Check if this chunk has any parts
            if not chunk.candidates or not chunk.candidates[0].content.parts:
                continue

            for part in chunk.candidates[0].content.parts:
                # Handle text content
                if hasattr(part, 'text') and part.text:
                    has_text_content = True
                    yield part.text

                # Handle function calls
                if hasattr(part, 'function_call') and part.function_call:
                    func_call = part.function_call

                    # Capture thought_signature if present (required for Gemini 3)
                    metadata = {}
                    if hasattr(part, 'thought_signature') and part.thought_signature:
                        metadata['thought_signature'] = part.thought_signature

                    tool_call = ToolCall(
                        id=f"{func_call.name}_{len(current_tool_calls)}",
                        name=func_call.name,
                        args=dict(func_call.args) if func_call.args else {},
                        metadata=metadata if metadata else None
                    )
                    current_tool_calls.append(tool_call)

        # Yield all tool calls after streaming is complete
        for tool_call in current_tool_calls:
            yield tool_call