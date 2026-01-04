import os
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Event(BaseModel):
    id: str
    time: datetime
    content: str
    metadata: Optional[Dict[str, Any]] = None


def format_events(events_queue: asyncio.Queue[Event]) -> str:
    """Format events from the queue into a readable string."""
    events_list = []
    while not events_queue.empty():
        events_list.append(events_queue.get_nowait())

    if not events_list:
        return ""

    time_str = events_list[0].time.strftime("%Y-%m-%d %H:%M:%S")
    return f"- [{time_str}] {events_list[0].content}"


def format_filesystem_overview(root_file_path: str) -> str:
    """
    Format the filesystem overview into a readable string only covering the root directory and the FIRST TWO levels of subdirectories.
    """
    lines = []
    try:
        # Level 0: Root directory contents
        root_items = sorted(os.listdir(root_file_path))
        for item in root_items:
            item_path = os.path.join(root_file_path, item)
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
