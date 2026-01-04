import os
from ame import AgentWithTools
from ame.core.agent_with_self_scheduling import LongRunningAgentWithFilesystem
from ame.llms.gemini.llm import LLM as GeminiLLM
from ame.core.chat_context import ChatMessage, ChatRole
import asyncio


async def main():
    cwd = os.getcwd()
    # Path to example directory in src/ame/examples/long_running/documentation
    path_to_example_directory = os.path.join(cwd, "src", "ame", "examples", "long_running", "documentation")
    agent = LongRunningAgentWithFilesystem(root_file_path=path_to_example_directory)
    while True:
        user_input = input("You: ")
        async for chunk in agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=user_input)):
            if isinstance(chunk, str):
                print(chunk)
        print("-" * 100)
if __name__ == "__main__":
    asyncio.run(main())