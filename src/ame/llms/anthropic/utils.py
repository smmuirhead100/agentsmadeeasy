from anthropic import types as anthropic_types
from ame.core.chat_context import ChatMessage, ChatRole
from ame.core.tools import Tool, ToolCall


def chat_messages_to_anthropic_system_and_messages(messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
    system_prompt = next((m.content for m in messages if m.role == ChatRole.SYSTEM), None)
    if not system_prompt:
        raise ValueError("No system prompt found!")

    anthropic_messages = []
    for msg in messages:
        role = "assistant" if msg.role == ChatRole.ASSISTANT else "user"
        if isinstance(msg.content, str):
            anthropic_messages.append(anthropic_types.MessageParam(role=role, content=msg.content))
        elif isinstance(msg.content, ToolCall):
            # Single tool call
            tool_call = msg.content
            tool_use_block = anthropic_types.ToolUseBlockParam(
                id=tool_call.id,
                input=tool_call.args or {},
                name=tool_call.name,
                type="tool_use",
            )
            tool_result_block = anthropic_types.ToolResultBlockParam(
                tool_use_id=tool_call.id,
                content=tool_call.response or "",
                is_error=False,
                type="tool_result",
            )
            # Assistant message with tool use
            anthropic_messages.append(anthropic_types.MessageParam(
                role="assistant",
                content=[tool_use_block]
            ))
            # User message with tool result
            anthropic_messages.append(anthropic_types.MessageParam(
                role="user",
                content=[tool_result_block]
            ))
        elif isinstance(msg.content, list) and all(isinstance(tc, ToolCall) for tc in msg.content):
            # Multiple tool calls
            tool_use_blocks = []
            tool_result_blocks = []
            for tool_call in msg.content:
                tool_use_blocks.append(anthropic_types.ToolUseBlockParam(
                    id=tool_call.id,
                    input=tool_call.args or {},
                    name=tool_call.name,
                    type="tool_use",
                ))
                tool_result_blocks.append(anthropic_types.ToolResultBlockParam(
                    tool_use_id=tool_call.id,
                    content=tool_call.response or "",
                    is_error=False,
                    type="tool_result",
                ))
            # Assistant message with all tool uses
            anthropic_messages.append(anthropic_types.MessageParam(
                role="assistant",
                content=tool_use_blocks
            ))
            # User message with all tool results
            anthropic_messages.append(anthropic_types.MessageParam(
                role="user",
                content=tool_result_blocks
            ))
        else:
            raise ValueError(f"Unknown message type: {type(msg.content)}")

    return system_prompt, anthropic_messages


def tool_to_anthropic_tool(tool: Tool) -> anthropic_types.ToolParam:
    return anthropic_types.ToolParam(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema.model_json_schema(),
    )