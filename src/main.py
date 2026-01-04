from datetime import datetime
import os
from ame.core.agent_with_self_scheduling import Event, LongRunningAgentWithFilesystem
from ame.core.chat_context import ChatMessage, ChatRole
import asyncio


async def main():
    cwd = os.getcwd()
    # Path to example directory in src/ame/examples/long_running/documentation
    path_to_example_directory = os.path.join(cwd, "src", "ame", "examples", "long_running", "documentation")
    agent = LongRunningAgentWithFilesystem(root_file_path=path_to_example_directory)
    while True:
        user_input = await asyncio.to_thread(input, "You: ")
        event = Event(time=datetime.now(), content=f"Text message from 714-742-2219: '{user_input}'")
        await agent.add_event(event)
        print("-" * 100)
if __name__ == "__main__":
    asyncio.run(main())