"""Tool descriptions for bash tools."""

BASH_DESCRIPTION = (
    "Executes a shell command in the workspace sandbox. "
    "Use for running CLI tools (dbt, pytest, git, pip), creating directories, or anything "
    "the file tools can't do.\n"
    "The command runs with the workspace as its working directory. "
    "Output (stdout + stderr combined) is streamed live to the user and returned to you "
    "after the command completes.\n"
    "Parameters:\n"
    "  - command (str): The shell command to execute.\n"
    "  - timeout (int, optional): Maximum seconds to wait for completion. Defaults to 120.\n"
    "Notes:\n"
    "  - System install commands (apt, apt-get, yum) are blocked.\n"
    "  - Output exceeding ~10k tokens is truncated; the tail is preserved."
)
