from datetime import datetime, timedelta
import asyncio
import subprocess
from typing import AsyncGenerator, List, Optional
from typing_extensions import override
import uuid

from ame.core.agent_with_tools import AgentWithTools
from ame.core.chat_context import ChatMessage, ChatRole
from ame.core.tools import ToolCall, tool
from ame.llms.gemini.llm import LLM as GeminiLLM
from ame.llms.llm import LLM
from .utils import Event, format_events, format_filesystem_overview

INSTRUCTIONS = """
# Identity
You are a generalized helpful assistant. You will be provided with a list of events. Based on the events, you will use the filesystem and tools to perform tasks. The current time in UTC is {current_time}.

# Filesystem
Everything you know is in your own filesystem. You are encouraged to leverage the filesystem to perform tasks, as well as update the filesystem to reflect your knowledge.

IMPORTANT: Any important events, knowledge, or tasks that you need to remember, you should update the filesystem to reflect your knowledge.

To give you an idea of the filesystem, here is a high-level overview of the filesystem:
{filesystem_overview}

# Skills
There is one special directory in your filesystem called "skills". This directory contains files that describe different skills you can perform.
You are encouraged to use the skills to perform tasks, as well as update the skills to reflect your knowledge.
You may also create new skills to perform tasks that are not already covered by the existing skills.

The skills directory must have the following structure:
```
skills/
|-- <skill_name>/
|   |-- SKILL.md  # This file contains the skill description. Always read this file before using the skill.
|   |-- <skill_name_example>.md  # Helper files that demonstrate how to use the skill.
|   |-- <skill_name_specification>.md  # Specific subset of the skill that is relevant to the task at hand.
|-- <skill_name_2>/
|   |-- SKILL.md
|   |-- <skill_name_2_example>.md
|   |-- <skill_name_2_specification>.md
|-- ...
```

# Events
Here is a list of events that have occurred:
{events}
"""

DEFAULT_LLM = GeminiLLM(enable_search=True)


class LongRunningAgentWithFilesystem(AgentWithTools):
    def __init__(self, llm: LLM = DEFAULT_LLM, root_file_path: str = "/") -> None:
        super().__init__(llm=llm, instructions=INSTRUCTIONS.format(current_time=datetime.now(), events="", filesystem_overview=""))
        self._root_file_path = root_file_path
        self._events_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._events_queue.put_nowait(Event(id=str(uuid.uuid4()), time=datetime.now(), content="You are now running.", metadata={"type": "system", "message": "You are now running."}))
        asyncio.create_task(self._run())

    @tool()
    async def run_bash_command(self, command: str) -> str:
        """
        This tool enables you to run a bash command on the filesystem. Use this tool if you need to perform a task that requires a bash command.

        :params:
            command: The bash command to run.
        :returns:
            The output of the bash command.
        """
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=self._root_file_path)
        return f"Output of the bash command: {result.stdout}"

    async def add_event(self, event: Event) -> None:
        self._events_queue.put_nowait(event)

    async def _run(self):
        while True:
            print(f"Thinking: {self._thinking}")
            print(f"Events queue size: {self._events_queue.qsize()}")

            if not self._thinking and self._events_queue.qsize() > 0:
                # Format the system instructions with the latest events and filesystem overview
                events_str = format_events(self._events_queue)
                filesystem_overview_str = format_filesystem_overview(self._root_file_path)
                self.update_instructions(INSTRUCTIONS.format(current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), events=events_str, filesystem_overview=filesystem_overview_str))
                self._messages = [m for m in self._messages if m.role == ChatRole.SYSTEM]

                print(f"================")
                print(next(m for m in self._messages if m.role == ChatRole.SYSTEM).content)
                print(f"================")
                async for chunk in self.astream():
                    print(chunk)
            await asyncio.sleep(1)