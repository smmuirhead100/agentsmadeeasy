from typing import Any, Dict, Optional, Type
from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]


class ToolCall(BaseModel):
    id: str
    name: str
    args: Optional[Dict[str, Any]] = None
    response: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def tool(func, end_turn: bool = False):
    func.is_tool = True
    func.end_turn = end_turn
    return func


# class User(BaseModel):
#     name: str = Field(description="The user's full name")
#     age: int = Field(ge=0, description="The user's age in years")


# tool = Tool(name="user", schema=User)
# print(tool.schema.model_json_schema())