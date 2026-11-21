"""The six tool implementations.

Every function returns a plain string: the tool result the model sees.
Errors are strings too, never exceptions. A failed call comes back as
a result marked as an error, and the model usually fixes its own
mistake on the next turn. That is what makes the loop self-repairing.

Safety rules, in one place:
- File writes and edits stay inside the output folder the user chose.
- Reads, lists, and searches stay inside the working folder or the
  output folder. Anything outside is refused.
- ``edit_file`` refuses to touch a file the agent has not read in this
  run, and warns if the file changed on disk since it was read.
- ``run_shell`` refuses a small blocklist of destructive commands
  outright, and asks the user to confirm anything not on the safe
  list. In headless runs (tests, CLI) confirmation auto-allows.
"""

import fnmatch
import os
import re
import subprocess
from pathlib import Path

from . import config
from .context import truncate_result

# Commands refused outright. Word boundaries stop "perform" matching "rm".
BLOCKLIST_PATTERNS = [
    r"\brm\b",
    r"\brmdir\b",
    r"\bdel\b",
    r"\bformat\b",
    r"\bsudo\b",
    r"\bmkfs\b",
    r"\bdd\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\b",
    r"\bpkill\b",
    r">\s*/dev/",
    r">>\s*/dev/",
    r"\bgit\s+push\s+--force\b",
    r"\bgit\s+push\s+-f\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-f",
    r"\bgit\s+checkout\s+\.\s*$",
]
BLOCKLIST = [re.compile(p) for p in BLOCKLIST_PATTERNS]

# Commands that run without asking. Anything else asks first in the GUI.
SAFE_COMMANDS = (
    "npm install",
    "npm test",
    "node --version",
    "ls",
    "dir",
    "python --version",
)

IGNORED_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", ".pytest_cache"}


class ToolContext:
    """Everything the tools need: folders, read tracking, confirmation."""

    def __init__(self, work_dir, output_dir, confirm=None):
        self.work_dir = Path(work_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # confirm(command) -> bool. None means auto-allow (headless runs).
        self.confirm = confirm if confirm is not None else (lambda command: True)
        # path (str) -> modification time when the agent last read it.
        self.read_files = {}

    def resolve_readable(self, file_path):
        """Resolve a path the agent may read. None when it is outside.

        A relative path is looked up in the working folder first, then
        the output folder, so files the agent just generated are found
        by name. An absolute path must sit inside one of the two.
        """
        path = Path(file_path)
        if path.is_absolute():
            resolved = path.resolve()
            if _inside(resolved, self.work_dir) or _inside(resolved, self.output_dir):
                return resolved
            return None
        for base in (self.work_dir, self.output_dir):
            resolved = (base / path).resolve()
            if resolved.is_file():
                return resolved
        return (self.work_dir / path).resolve()

    def resolve_writable(self, file_path):
        """Resolve a path the agent may write. None when it is outside."""
        resolved = _resolve(self.output_dir, file_path)
        if _inside(resolved, self.output_dir):
            return resolved
        return None


def _resolve(base, file_path):
    path = Path(file_path)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _inside(path, base):
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- read_file

def read_file(ctx, file_path, offset=1, limit=None):
    """Read a file, returned with line numbers."""
    resolved = ctx.resolve_readable(file_path)
    if resolved is None:
        return "Error: path is outside the working folder: {}".format(file_path)
    if not resolved.is_file():
        return "Error: file not found: {}".format(file_path)
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "Error: could not read {}: {}".format(file_path, exc)
    ctx.read_files[str(resolved)] = resolved.stat().st_mtime
    lines = text.splitlines()
    offset = max(1, int(offset or 1))
    if limit is not None:
        lines = lines[offset - 1: offset - 1 + int(limit)]
    else:
        lines = lines[offset - 1:]
    numbered = "\n".join(
        "{:>6}  {}".format(i, line) for i, line in enumerate(lines, start=offset)
    )
    return truncate_result(numbered)


# --------------------------------------------------------------- write_file

def write_file(ctx, file_path, content):
    """Create a new file. Refuses to overwrite a non-empty file."""
    if content is None:
        return "Error: write_file needs a content argument."
    if len(content) > config.MAX_FILE_WRITE_CHARS:
        return (
            "Error: content is {} characters, over the {} character limit "
            "for one file. Split the file into smaller pieces.".format(
                len(content), config.MAX_FILE_WRITE_CHARS
            )
        )
    resolved = ctx.resolve_writable(file_path)
    if resolved is None:
        return "Error: path is outside the output folder: {}".format(file_path)
    if resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0:
        return (
            "Error: {} already exists and is not empty. "
            "Use edit_file to change an existing file.".format(file_path)
        )
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
    except OSError as exc:
        return "Error: could not write {}: {}".format(file_path, exc)
    return "Wrote {} ({} characters).".format(file_path, len(content))


# ---------------------------------------------------------------- edit_file

def edit_file(ctx, file_path, old_string, new_string, replace_all=False):
    """Search-and-replace edit. Needs exactly one match unless replace_all."""
    resolved = ctx.resolve_writable(file_path)
    if resolved is None:
        return "Error: path is outside the output folder: {}".format(file_path)
    if not resolved.is_file():
        return "Error: file not found: {}".format(file_path)
    key = str(resolved)
    if key not in ctx.read_files:
        return (
            "Error: edit refused. Read {} with read_file first, so the "
            "edit is based on the file's real contents.".format(file_path)
        )
    warning = ""
    if resolved.stat().st_mtime != ctx.read_files[key]:
        warning = (
            "Warning: {} changed on disk since it was read. "
            "The edit was applied anyway; re-read the file to check it.\n".format(
                file_path
            )
        )
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "Error: could not read {}: {}".format(file_path, exc)
    count = text.count(old_string)
    if count == 0:
        return (
            "Error: the text to replace was not found in {}. "
            "Re-read the file and copy the exact text.".format(file_path)
        )
    if count > 1 and not replace_all:
        return (
            "Error: the text to replace appears {} times in {}. "
            "Give more surrounding context so it matches exactly once, "
            "or set replace_all to true.".format(count, file_path)
        )
    if replace_all:
        text = text.replace(old_string, new_string)
        made = count
    else:
        text = text.replace(old_string, new_string, 1)
        made = 1
    try:
        resolved.write_text(text, encoding="utf-8")
    except OSError as exc:
        return "Error: could not write {}: {}".format(file_path, exc)
    ctx.read_files[key] = resolved.stat().st_mtime
    return "{}Replaced {} occurrence(s) in {}.".format(warning, made, file_path)


# --------------------------------------------------------------- list_files

def list_files(ctx, pattern="**/*", path=None):
    """List files matching a glob. Ignores node_modules and .git."""
    base = ctx.work_dir if path is None else ctx.resolve_readable(path)
    if base is None:
        return "Error: path is outside the working folder: {}".format(path)
    if not base.is_dir():
        return "Error: folder not found: {}".format(path or str(ctx.work_dir))
    try:
        found = sorted(
            str(p.relative_to(base))
            for p in base.glob(pattern)
            if p.is_file() and not any(part in IGNORED_DIRS for part in p.parts)
        )
    except (OSError, ValueError) as exc:
        return "Error: could not list files: {}".format(exc)
    if len(found) > config.MAX_LIST_LINES:
        note = "\n[... showing {} of {} files ...]".format(
            config.MAX_LIST_LINES, len(found)
        )
        found = found[: config.MAX_LIST_LINES]
    else:
        note = ""
    if not found:
        return "No files matched '{}'.".format(pattern)
    return "\n".join(found) + note


# -------------------------------------------------------------- grep_search

def grep_search(ctx, pattern, path=None, include=None):
    """Find a regex across files. Pure Python, so it works on Windows too."""
    base = ctx.work_dir if path is None else ctx.resolve_readable(path)
    if base is None:
        return "Error: path is outside the working folder: {}".format(path)
    if not base.exists():
        return "Error: path not found: {}".format(path or str(ctx.work_dir))
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return "Error: bad search pattern {!r}: {}".format(pattern, exc)
    matches = []
    roots = [base] if base.is_file() else list(_walk_files(base))
    for file_path in roots:
        if include and not fnmatch.fnmatch(file_path.name, include):
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(
                    "{}:{}: {}".format(
                        file_path.relative_to(base) if file_path != base else file_path.name,
                        number,
                        line.strip()[:300],
                    )
                )
                if len(matches) >= config.MAX_GREP_LINES:
                    break
        if len(matches) >= config.MAX_GREP_LINES:
            break
    if not matches:
        return "No matches for {!r}.".format(pattern)
    result = "\n".join(matches)
    if len(matches) >= config.MAX_GREP_LINES:
        result += "\n[... showing first {} matches ...]".format(config.MAX_GREP_LINES)
    return result


def _walk_files(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in sorted(files):
            yield Path(root) / name


# --------------------------------------------------------------- run_shell

def run_shell(ctx, command, timeout=config.SHELL_TIMEOUT_SECONDS):
    """Run a shell command. Blocklist first, confirmation second."""
    if not command or not command.strip():
        return "Error: run_shell needs a command."
    for blocked in BLOCKLIST:
        if blocked.search(command):
            return (
                "Error: command refused by the safety blocklist: {!r}. "
                "Blocked commands are never run.".format(command)
            )
    if not _is_safe(command):
        if not ctx.confirm(command):
            return "Error: command not confirmed by the user; not run."
    try:
        proc = _start_process(command, ctx)
    except OSError as exc:
        return "Error: could not run command: {}".format(exc)
    timeout = int(timeout or config.SHELL_TIMEOUT_SECONDS)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        proc.communicate()
        return "Error: command timed out after {} seconds: {!r}".format(timeout, command)
    stdout = stdout or ""
    stderr = stderr or ""
    limit = config.SHELL_OUTPUT_MAX_BYTES // 2
    if len(stdout) > limit:
        stdout = stdout[:limit] + "\n[... stdout cut ...]"
    if len(stderr) > limit:
        stderr = stderr[:limit] + "\n[... stderr cut ...]"
    return "Exit code: {}\nstdout:\n{}\nstderr:\n{}".format(returncode, stdout, stderr)


def _start_process(command, ctx):
    kwargs = dict(
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        cwd=str(ctx.work_dir),
    )
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(command, **kwargs)


def _kill_process_tree(proc):
    # A timeout must kill the whole tree: if only the shell dies, its
    # children keep the pipes open and communicate() blocks forever.
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait()


def _is_safe(command):
    """True when the command starts with a known-safe command."""
    stripped = command.strip()
    for safe in SAFE_COMMANDS:
        if " " in safe:
            if stripped == safe or stripped.startswith(safe + " "):
                return True
        elif stripped.split(" ", 1)[0] == safe:
            return True
    return False
