from google.genai import types as gemini_types
from ame.core.chat_context import ChatMessage, ChatRole
from ame.core.tools import Tool, ToolCall


def chat_messages_to_gemini_system_and_contents(messages: list[ChatMessage]) -> tuple[str, list[gemini_types.Content]]:
    """Convert ChatMessages to Gemini system prompt and contents list."""
    system_prompt = next((m.content for m in messages if m.role == ChatRole.SYSTEM), None)
    if not system_prompt:
        raise ValueError("No system prompt found!")

    gemini_contents = []
    for msg in messages:
        if msg.role == ChatRole.SYSTEM:
            # Skip system messages as they're extracted separately
            continue

        role = "model" if msg.role == ChatRole.ASSISTANT else "user"

        if isinstance(msg.content, str):
            # Simple text message
            gemini_contents.append(
                gemini_types.Content(
                    role=role,
                    parts=[gemini_types.Part(text=msg.content)]
                )
            )
        elif isinstance(msg.content, ToolCall):
            # Single tool call - add both the function call and response
            tool_call = msg.content

            # Extract thought_signature from metadata if present
            thought_signature = None
            if tool_call.metadata and 'thought_signature' in tool_call.metadata:
                thought_signature = tool_call.metadata['thought_signature']

            # Assistant message with function call
            part_kwargs = {
                "function_call": gemini_types.FunctionCall(
                    name=tool_call.name,
                    args=tool_call.args or {}
                )
            }
            if thought_signature is not None:
                part_kwargs["thought_signature"] = thought_signature

            gemini_contents.append(
                gemini_types.Content(
                    role="model",
                    parts=[gemini_types.Part(**part_kwargs)]
                )
            )

            # User message with function response
            gemini_contents.append(
                gemini_types.Content(
                    role="user",
                    parts=[gemini_types.Part.from_function_response(
                        name=tool_call.name,
                        response={"result": tool_call.response or ""}
                    )]
                )
            )
        elif isinstance(msg.content, list) and all(isinstance(tc, ToolCall) for tc in msg.content):
            # Multiple tool calls
            function_call_parts = []
            function_response_parts = []

            for tool_call in msg.content:
                # Extract thought_signature from metadata if present
                thought_signature = None
                if tool_call.metadata and 'thought_signature' in tool_call.metadata:
                    thought_signature = tool_call.metadata['thought_signature']

                # Build Part with function_call and optional thought_signature
                part_kwargs = {
                    "function_call": gemini_types.FunctionCall(
                        name=tool_call.name,
                        args=tool_call.args or {}
                    )
                }
                if thought_signature is not None:
                    part_kwargs["thought_signature"] = thought_signature

                function_call_parts.append(gemini_types.Part(**part_kwargs))
                function_response_parts.append(
                    gemini_types.Part.from_function_response(
                        name=tool_call.name,
                        response={"result": tool_call.response or ""}
                    )
                )

            # Assistant message with all function calls
            gemini_contents.append(
                gemini_types.Content(
                    role="model",
                    parts=function_call_parts
                )
            )

            # User message with all function responses
            gemini_contents.append(
                gemini_types.Content(
                    role="user",
                    parts=function_response_parts
                )
            )
        else:
            raise ValueError(f"Unknown message type: {type(msg.content)}")

    return system_prompt, gemini_contents


def tool_to_gemini_function_declaration(tool: Tool) -> dict:
    """Convert a Tool to Gemini function declaration format."""
    schema = tool.input_schema.model_json_schema()

    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": {
            "type": schema.get("type", "object"),
            "properties": schema.get("properties", {}),
            "required": schema.get("required", [])
        }
    }