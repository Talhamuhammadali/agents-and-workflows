"""
Filesystem & Shell Tools Available to Claude Code
===================================================

This module documents all filesystem and shell tools available.

Tools Overview:
1. Read - Read files
2. Write - Create/overwrite files
3. Edit - String replacement in files
4. Glob - Find files by pattern
5. Grep - Search file contents
6. Bash - Execute shell commands
"""

TOOLS = {
    "Read": {
        "description": "Reads a file from the local filesystem. Supports text files, images, PDFs, and Jupyter notebooks.",
        "parameters": {
            "file_path": {
                "type": "string",
                "required": True,
                "description": "Absolute path to the file to read.",
            },
            "offset": {
                "type": "integer",
                "required": False,
                "description": "Line number to start reading from (0-based).",
            },
            "limit": {
                "type": "integer",
                "required": False,
                "description": "Number of lines to read. Default reads up to 2000 lines.",
            },
            "pages": {
                "type": "string",
                "required": False,
                "description": "Page range for PDF files (e.g., '1-5', '3', '10-20'). Max 20 pages per request.",
            },
        },
    },
    "Write": {
        "description": "Creates a new file or completely overwrites an existing one.",
        "parameters": {
            "file_path": {
                "type": "string",
                "required": True,
                "description": "Absolute path to the file to write.",
            },
            "content": {
                "type": "string",
                "required": True,
                "description": "The content to write to the file.",
            },
        },
    },
    "Edit": {
        "description": "Performs exact string replacements in files. The old_string must be unique in the file unless replace_all is True.",
        "parameters": {
            "file_path": {
                "type": "string",
                "required": True,
                "description": "Absolute path to the file to modify.",
            },
            "old_string": {
                "type": "string",
                "required": True,
                "description": "The exact text to find and replace.",
            },
            "new_string": {
                "type": "string",
                "required": True,
                "description": "The replacement text (must differ from old_string).",
            },
            "replace_all": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "If True, replaces all occurrences of old_string. Default is False.",
            },
        },
    },
    "Glob": {
        "description": "Fast file pattern matching. Returns matching file paths sorted by modification time.",
        "parameters": {
            "pattern": {
                "type": "string",
                "required": True,
                "description": "Glob pattern to match (e.g., '**/*.py', 'src/**/*.ts').",
            },
            "path": {
                "type": "string",
                "required": False,
                "description": "Directory to search in. Defaults to current working directory.",
            },
        },
    },
    "Grep": {
        "description": "Searches file contents using regex patterns. Powered by ripgrep.",
        "parameters": {
            "pattern": {
                "type": "string",
                "required": True,
                "description": "Regex pattern to search for (e.g., 'log.*Error', 'function\\s+\\w+').",
            },
            "path": {
                "type": "string",
                "required": False,
                "description": "File or directory to search in. Defaults to current working directory.",
            },
            "glob": {
                "type": "string",
                "required": False,
                "description": "Glob pattern to filter files (e.g., '*.js', '*.{ts,tsx}').",
            },
            "type": {
                "type": "string",
                "required": False,
                "description": "File type filter (e.g., 'js', 'py', 'rust'). More efficient than glob for standard types.",
            },
            "output_mode": {
                "type": "string",
                "required": False,
                "default": "files_with_matches",
                "description": "Output mode: 'content' (matching lines), 'files_with_matches' (file paths), 'count' (match counts).",
            },
            "-A": {
                "type": "number",
                "required": False,
                "description": "Number of lines to show after each match. Requires output_mode='content'.",
            },
            "-B": {
                "type": "number",
                "required": False,
                "description": "Number of lines to show before each match. Requires output_mode='content'.",
            },
            "-C": {
                "type": "number",
                "required": False,
                "description": "Number of context lines before and after each match. Alias: 'context'.",
            },
            "-i": {
                "type": "boolean",
                "required": False,
                "description": "Case insensitive search.",
            },
            "-n": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Show line numbers in output. Requires output_mode='content'.",
            },
            "multiline": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Enable multiline mode where '.' matches newlines and patterns can span lines.",
            },
            "head_limit": {
                "type": "number",
                "required": False,
                "default": 250,
                "description": "Limit output to first N lines/entries. Pass 0 for unlimited.",
            },
            "offset": {
                "type": "number",
                "required": False,
                "default": 0,
                "description": "Skip first N lines/entries before applying head_limit.",
            },
        },
    },
    "Bash": {
        "description": "Executes shell commands and returns output. Used for system commands, git, npm, and any terminal operation.",
        "parameters": {
            "command": {
                "type": "string",
                "required": True,
                "description": "The shell command to execute.",
            },
            "description": {
                "type": "string",
                "required": False,
                "description": "Short description of what the command does (for user review).",
            },
            "timeout": {
                "type": "number",
                "required": False,
                "default": 120000,
                "description": "Timeout in milliseconds. Max 600000 (10 minutes). Default 120000 (2 minutes).",
            },
            "run_in_background": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "If True, runs the command in the background. You get notified when it completes.",
            },
        },
    },
}
