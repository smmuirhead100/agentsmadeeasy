from ame.core.agent_with_tools import AgentWithTools

class AgentWithFilesystem(AgentWithTools):
    def __init__(self, root_file_path: str) -> None:
        self.root_file_path = root_file_path

    @tool
    def run_bash_command(self, command: str) -> str:
        """Runs a bash command and returns the output."""
        return subprocess.run(command, shell=True, capture_output=True, text=True).stdout