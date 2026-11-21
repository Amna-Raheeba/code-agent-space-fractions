"""Tool schemas (OpenAI function format) and the dispatch table.

Each tool carries its own instructions in its description field, so the
model learns how to use it from the schema itself. The registry maps
tool names to the implementation functions in tools_impl.py. Unknown
tool names are an error result, never a crash.
"""

from . import tools_impl

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file. Returns the content with "
                "line numbers. Use this before editing a file. Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "First line to read (1-based).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum lines to read.",
                    },
                },
                "required": ["file_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create a new file with the given content. Creates missing "
                "parent folders. Use only for new files; use edit_file for "
                "files that already exist. Refuses to overwrite a non-empty "
                "file, and refuses content over 60,000 characters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path of the file to create, inside the output folder.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full contents of the new file.",
                    },
                },
                "required": ["file_path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Change part of an existing file by search and replace. "
                "The old_string must match exactly once, or set "
                "replace_all to true. Read the file with read_file first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path of the file to change, inside the output folder.",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Exact text to replace.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace every occurrence. Default false.",
                    },
                },
                "required": ["file_path", "old_string", "new_string"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files matching a glob pattern, such as **/*.js. "
                "Skips node_modules and .git. Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern, for example **/*.js.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Folder to list, relative to the working folder.",
                    },
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": (
                "Search file contents for a regular expression. Returns "
                "matching lines with file names and line numbers. Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Folder or file to search, relative to the working folder.",
                    },
                    "include": {
                        "type": "string",
                        "description": "Only search files matching this glob, for example *.js.",
                    },
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a shell command, for example to install dependencies "
                "or run tests. Returns the exit code, stdout, and stderr. "
                "Destructive commands are refused. Commands outside a "
                "small safe list ask the user to confirm first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds before the command is stopped. Default 30.",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_NAMES = [schema["function"]["name"] for schema in TOOL_SCHEMAS]

# name -> implementation. Each takes (ctx, **arguments) and returns a string.
REGISTRY = {
    "read_file": tools_impl.read_file,
    "write_file": tools_impl.write_file,
    "edit_file": tools_impl.edit_file,
    "list_files": tools_impl.list_files,
    "grep_search": tools_impl.grep_search,
    "run_shell": tools_impl.run_shell,
}


def execute_tool(ctx, name, arguments):
    """Run one tool call and return its result string. Never raises.

    Unknown tool names, missing arguments, and wrong argument types
    all come back as error strings the model can read and recover from.
    """
    func = REGISTRY.get(name)
    if func is None:
        return (
            "Error: unknown tool {!r}. Available tools are: {}.".format(
                name, ", ".join(TOOL_NAMES)
            )
        )
    if not isinstance(arguments, dict):
        return "Error: tool arguments must be a JSON object, got {!r}.".format(
            type(arguments).__name__
        )
    try:
        return func(ctx, **arguments)
    except TypeError as exc:
        return "Error: bad arguments for {}: {}.".format(name, exc)
    except Exception as exc:  # noqa: BLE001 - tool failures are data, not crashes
        return "Error: {} failed: {}.".format(name, exc)
