"""Central registry for tools and skills."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from agentic_patterns.shared.ask_tool import ask_question
from agentic_patterns.shared.bash_tools import bash, glob_search, grep_search
from agentic_patterns.shared.todos import update_todos
from agentic_patterns.shared.workspace_tools import edit_file, read_file, write_file


@dataclass
class Skill:
    """Parsed SKILL.md — metadata + instruction body."""

    name: str
    description: str
    allowed_tools: list[str]  # Only tool names
    version: str
    instructions: str


SKILLS: dict[str, Skill] = {}
TOOLS_BY_NAME: dict[str, Any] = {}

# Tools every agent has access to by default
ESSENTIAL_TOOL_NAMES: list[str] = ["Todos", "Ask", "Skill"]

# Default skill library, this dir is auto-loaded.
LIBRARY_DIR: Path = Path(__file__).parent / "skills"

# Tools mapped by name for easy resolution when loading skills. Seeded with shared/ tools.
for _t in (
    ask_question,  # "Ask"
    update_todos,  # "Todos"
    bash,  # "bash"
    grep_search,  # "Grep"
    glob_search,  # "Glob"
    read_file,  # "Read"
    write_file,  # "Write"
    edit_file,  # "Edit"
):
    TOOLS_BY_NAME[_t.name] = _t


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return ``(yaml_block, body)``. Raises if the file has no leading '---' block."""
    if not text.startswith("---"):
        raise ValueError("SKILL.md must start with a '---' frontmatter block")
    _, rest = text.split("---", 1)
    fm_raw, _, body = rest.partition("\n---")
    return fm_raw.strip(), body.lstrip("\n")


def register(skill_path: Path) -> None:
    """Parse a SKILL.md file and add the resulting Skill to SKILLS.

    No dedup by design: a later file with the same name silently overwrites
    an earlier one.
    """
    fm_raw, body = _split_frontmatter(skill_path.read_text())
    fm = yaml.safe_load(fm_raw) or {}

    tools_str = str(fm.get("allowed-tools", ""))
    allowed_tools = [t.strip() for t in tools_str.split(",") if t.strip()]

    SKILLS[fm["name"]] = Skill(
        name=fm["name"],
        description=fm.get("description", ""),
        allowed_tools=allowed_tools,
        version=str(fm.get("version", "0.0.0")),
        instructions=body.strip(),
    )


def resolve(names: list[str]) -> list[Any]:
    """Tool NAMES -> tool OBJECTS. Raises ``KeyError`` on unknown names (intentional)."""
    return [TOOLS_BY_NAME[n] for n in names]


# Auto-discover every skill under LIBRARY_DIR. Drop a new ``<name>/SKILL.md``
# folder and it registers on next import.
if LIBRARY_DIR.exists():
    for _skill_md in LIBRARY_DIR.glob("*/SKILL.md"):
        register(_skill_md)
