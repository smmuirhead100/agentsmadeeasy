from typing import Any, Dict, Optional, Type
from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]
    end_turn: bool = False


class ToolCall(BaseModel):
    id: str
    name: str
    args: Optional[Dict[str, Any]] = None
    response: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def tool(func=None, end_turn: bool = False):
    def decorator(f):
        f.is_tool = True
        f.end_turn = end_turn
        return f

    if func is None:
        # Called with arguments: @tool(end_turn=True)
        return decorator
    else:
        # Called without arguments: @tool
        return decorator(func)


# class User(BaseModel):
#     name: str = Field(description="The user's full name")
#     age: int = Field(ge=0, description="The user's age in years")


# tool = Tool(name="user", schema=User)
# print(tool.schema.model_json_schema())