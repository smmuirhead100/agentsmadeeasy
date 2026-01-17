from google.genai import types as gemini_types
from ame.core.chat_context import ChatMessage, ChatRole
from ame.core.tools import Tool, ToolCall


def chat_messages_to_gemini_system_and_contents(messages: list[ChatMessage]) -> tuple[str, list[gemini_types.Content]]:
    """Convert ChatMessages to Gemini system prompt and contents list."""
    system_prompt = next((m.content for m in messages if m.role == ChatRole.SYSTEM), None)
    if not system_prompt:
        raise ValueError("No system prompt found!")

    gemini_contents = []
    # Gemini requires a user message, so if there is no user message, add an empty one at the beginning.
    if not any(m.role == ChatRole.USER for m in messages):
        gemini_contents.append(
            gemini_types.Content(
                role="user",
                parts=[gemini_types.Part(text="")]
            )
        )

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


def _clean_schema_for_gemini(schema: dict) -> dict:
    """Recursively clean a JSON schema to remove fields unsupported by Gemini."""
    if not isinstance(schema, dict):
        return schema

    # Fields that Gemini doesn't support
    unsupported_keys = {"additionalProperties", "additional_properties", "$defs", "title", "default"}

    cleaned = {}
    for key, value in schema.items():
        if key in unsupported_keys:
            continue

        # Handle anyOf - simplify by taking the first non-null type
        if key == "anyOf" and isinstance(value, list):
            # Filter out null types and take the first real type
            non_null_types = [v for v in value if not (isinstance(v, dict) and v.get("type") == "null")]
            if non_null_types:
                # Merge the first non-null type into the parent
                cleaned.update(_clean_schema_for_gemini(non_null_types[0]))
            continue

        # Recursively clean nested structures
        if isinstance(value, dict):
            cleaned[key] = _clean_schema_for_gemini(value)
        elif isinstance(value, list):
            cleaned[key] = [_clean_schema_for_gemini(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value

    return cleaned


def tool_to_gemini_function_declaration(tool: Tool) -> dict:
    """Convert a Tool to Gemini function declaration format."""
    schema = tool.input_schema.model_json_schema()

    # Clean properties to remove unsupported Gemini fields
    cleaned_properties = {}
    for prop_name, prop_schema in schema.get("properties", {}).items():
        cleaned_properties[prop_name] = _clean_schema_for_gemini(prop_schema)

    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": {
            "type": schema.get("type", "object"),
            "properties": cleaned_properties,
            "required": schema.get("required", [])
        }
    }