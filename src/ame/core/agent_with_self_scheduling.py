from datetime import datetime, timedelta
import asyncio
import os
import subprocess
from typing import AsyncGenerator, List

from pydantic import BaseModel
from ame.core.agent_with_tools import AgentWithTools
from ame.core.chat_context import ChatMessage, ChatRole
from ame.core.tools import ToolCall, tool
from ame.llms.gemini.llm import LLM as GeminiLLM
from ame.llms.llm import LLM

INSTRUCTIONS = """
You are a helpful assistant. You will be provided with documentation and a list of events. Based on the events, you will use the documentation to perform tasks. The current time is {current_time}.

# Documentation
There is one special directory in your filesystem called "skills". This directory contains files that describe the skills you can perform.
All other files in the filesystem are arbitrarily organized by you and you can read and write to them.

Here is a high level overview of the filesystem:
{filesystem_overview}

# Events
Events are things that have happened in the real world. Below is a list of events that have occurred since the last time you were run:
{events}
"""

DEFAULT_LLM = GeminiLLM()


class Event(BaseModel):
    time: datetime
    content: str


class LongRunningAgentWithFilesystem(AgentWithTools):
    def __init__(self, llm: LLM = DEFAULT_LLM, root_file_path: str = "/") -> None:
        super().__init__(llm=llm, instructions=INSTRUCTIONS.format(current_time=datetime.now(), events="", filesystem_overview=""))
        self._scheduled_tasks = []
        self._root_file_path = root_file_path
        self._events: List[Event] = []
        self._events_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._events_queue.put_nowait(Event(time=datetime.now(), content="You are now running."))
        asyncio.create_task(self._run_scheduled_tasks())

    def _format_events(self) -> str:
        """Format events from the queue into a readable string."""
        if self._events_queue.empty():
            return "No new events."

        events_list = []
        while not self._events_queue.empty():
            event = self._events_queue.get_nowait()
            events_list.append(event)

        if not events_list:
            return "No new events."

        formatted_events = []
        for event in events_list:
            time_str = event.time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_events.append(f"- [{time_str}] {event.content}")

        return "\n".join(formatted_events)

    def _format_filesystem_overview(self) -> str:
        """
        Format the filesystem overview into a readable string only covering the root directory and the FIRST TWO levels of subdirectories.
        """
        lines = []
        try:
            # Level 0: Root directory contents
            root_items = sorted(os.listdir(self._root_file_path))
            for item in root_items:
                item_path = os.path.join(self._root_file_path, item)
                is_dir = os.path.isdir(item_path)
                lines.append(f"{item}{'/' if is_dir else ''}")

                # Level 1: First level subdirectories
                if is_dir:
                    try:
                        level1_items = sorted(os.listdir(item_path))
                        for subitem in level1_items:
                            subitem_path = os.path.join(item_path, subitem)
                            is_subdir = os.path.isdir(subitem_path)
                            lines.append(f"  {subitem}{'/' if is_subdir else ''}")

                            # Level 2: Second level subdirectories
                            if is_subdir:
                                try:
                                    level2_items = sorted(os.listdir(subitem_path))
                                    for subsubitem in level2_items:
                                        subsubitem_path = os.path.join(subitem_path, subsubitem)
                                        is_subsubdir = os.path.isdir(subsubitem_path)
                                        lines.append(f"    {subsubitem}{'/' if is_subsubdir else ''}")
                                except (PermissionError, OSError):
                                    lines.append(f"    [Error reading directory]")
                    except (PermissionError, OSError):
                        lines.append(f"  [Error reading directory]")

            return "\n".join(lines) if lines else "Empty directory"
        except (PermissionError, OSError) as e:
            return f"Error reading filesystem: {e}"

    async def astream(self, *args, **kwargs) -> AsyncGenerator[str | ToolCall]:
        events_str = self._format_events()
        filesystem_overview_str = self._format_filesystem_overview()
        self.update_instructions(INSTRUCTIONS.format(current_time=datetime.now(), events=events_str, filesystem_overview=filesystem_overview_str))
        async for chunk in super().astream(*args, **kwargs):
            yield chunk

    async def add_event(self, event: Event) -> None:
        self._events_queue.put_nowait(event)
        self._events.append(event)

    @tool()
    async def schedule_self(self, schedule_in_seconds: int, context: str) -> str:
        """
        This tool enables you to schedule yourself to run at a particular time. Use this tool if you do not think you should take any action but may want to in a bit.

        :params:
            schedule_in_seconds: In how many seconds will you schedule yourself to run?
            context: A string describing the context of the scheduled task. This will be passed as context to yourself when the time comes to run the scheduled task.
        :returns:
            A string describing the scheduled task and the time it will run at.
        """
        now = datetime.now()
        scheduled_time = now + timedelta(seconds=schedule_in_seconds)
        self._scheduled_tasks.append((scheduled_time, context))
        return f"Scheduled self to run at {scheduled_time}"

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

    @tool()
    async def send_text_message(self, message: str, number: str) -> str:
        """
        This tool enables you to send a text message to a number. Use this tool if you need to send a text message to a number.

        :params:
            message: The message to send.
            number: The number to send the message to.
        :returns:
            A string describing the text message that was sent.
        """
        print(f"Sending text message to {number}: {message}")
        return f"Text message sent to {number}: {message}"

    async def _run_scheduled_tasks(self):
        while True:
            now = datetime.now()
            for scheduled_time, context in self._scheduled_tasks:
                if scheduled_time <= now:
                    self._scheduled_tasks.remove((scheduled_time, context))
                    async for chunk in self.astream(chat_message=ChatMessage(role=ChatRole.ASSISTANT, content=f"Running scheduled task at {scheduled_time}. Here is your context: {context}.")):
                        pass
            if not self._thinking and self._events_queue.qsize() > 0:
                async for chunk in self.astream():
                    pass
            await asyncio.sleep(1)
