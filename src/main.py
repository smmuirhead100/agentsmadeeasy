from datetime import datetime
import os
import asyncio
import uuid
import logging

from ame.examples.long_running.agent import LongRunningAgentWithFilesystem
from ame.examples.long_running.utils import Event

logger = logging.getLogger(__name__)


async def main():
    cwd = os.getcwd()
    # Path to example directory in src/ame/examples/long_running/documentation
    path_to_example_directory = os.path.join(cwd, "src", "ame", "examples", "long_running", "documentation")
    agent = LongRunningAgentWithFilesystem(root_file_path=path_to_example_directory)
    while True:
        user_input = await asyncio.to_thread(input, "You: ")
        event = Event(id=str(uuid.uuid4()), time=datetime.now(), content=f"Text message from 714-742-2219: '{user_input}'", metadata={"from": "714-742-2219", "to": "714-742-2219", "type": "text", "message": user_input})
        await agent.add_event(event)
        print("-" * 100)
if __name__ == "__main__":
    asyncio.run(main())