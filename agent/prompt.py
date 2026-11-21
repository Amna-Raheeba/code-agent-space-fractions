"""System prompt assembly and the fixed messages of the loop.

The system prompt is assembled at runtime from a template plus facts
gathered at startup (working folder, platform, date, tool versions).
It stays identical across turns so the provider's prompt cache can
hit. The task itself goes in as the first user message, not the system
prompt: task data belongs in the conversation, where it can be replaced
by compaction if needed.
"""

import json
import platform
import shutil
import sys
from datetime import date

from . import config

DELIVERABLES = (
    "project directory layout and full source code files",
    "dependency manifest (package.json and/or requirements.txt)",
    "project README",
    "test cases",
)


def build_system_prompt(work_dir):
    """Assemble the system prompt. Facts that cannot be gathered are left out."""
    facts = [
        "Working directory: {}".format(work_dir),
        "Operating system: {} {}".format(platform.system(), platform.release()),
        "Date: {}".format(date.today().isoformat()),
        "Python: {}".format(sys.version.split()[0]),
    ]
    node = shutil.which("node")
    if node:
        facts.append("Node.js is available.")
    else:
        facts.append("Node.js is not on this machine.")
    facts.append("Model: {} (DeepSeek API).".format(config.MODEL_ID))

    return (
        "You are a code generation agent. You generate a complete "
        "software project from architecture documents.\n\n"
        "Rules:\n"
        "- Read files before editing them. Use edit_file for existing "
        "files and write_file only for new files.\n"
        "- Use the dedicated file tools, not shell commands, to read "
        "and search files.\n"
        "- Never invent file contents you have not read. Never invent "
        "requirements the architecture documents do not state. If the "
        "documents leave something out, say so in the project README "
        "instead of guessing.\n"
        "- Write tests for what you generate.\n"
        "- Stop when the project is complete and say so in plain text. "
        "Do not call tools after the work is done.\n\n"
        "Environment:\n"
        + "\n".join("- " + fact for fact in facts)
        + "\n\n"
        "Deliverables (all of them, inside the output folder):\n"
        + "\n".join("- " + item for item in DELIVERABLES)
        + "\n"
        "- A Dockerfile only if the task asks for one.\n"
        "- Every file you claim to have written must exist on disk "
        "when the run ends.\n"
    )


def task_message(spec, extra_instructions=None):
    """First user message: the preprocessed architecture spec as JSON."""
    spec_text = json.dumps(spec, indent=2, ensure_ascii=False)
    message = (
        "Generate the complete project described by this architecture "
        "specification. Follow it as written: same components, same "
        "stack, same APIs, same data models. Do not redesign the system.\n\n"
        "```json\n" + spec_text + "\n```\n\n"
        "Work in the output folder. Create the project layout, write "
        "every source file, the dependency manifest, the README, and "
        "the tests. Run the tests with run_shell when you are done, and "
        "fix anything that fails. When everything is written and the "
        "tests pass, finish with a short plain-text summary: what was "
        "built, where it is, and what is still missing, if anything."
    )
    if extra_instructions:
        message += "\n\nExtra instructions from the user:\n" + extra_instructions
    return message


def continuation_message():
    """Sent when a reply was cut off by the output token limit."""
    return {
        "role": "user",
        "content": (
            "Output token limit hit. Resume directly, no apology, "
            "no recap. Pick up mid-thought."
        ),
    }
