"""Tests for the six tools: happy path, missing file, bad arguments."""

import os
import sys
import time

import pytest

from agent.tools import execute_tool
from agent.tools_impl import ToolContext


@pytest.fixture
def ctx(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    return ToolContext(work, out)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------- read_file

def test_read_file_returns_numbered_lines(ctx):
    _write(ctx.work_dir / "notes.txt", "alpha\nbeta\ngamma\n")
    result = execute_tool(ctx, "read_file", {"file_path": "notes.txt"})
    assert "1  alpha" in result
    assert "3  gamma" in result


def test_read_file_with_offset_and_limit(ctx):
    _write(ctx.work_dir / "notes.txt", "one\ntwo\nthree\nfour\n")
    result = execute_tool(
        ctx, "read_file", {"file_path": "notes.txt", "offset": 2, "limit": 2}
    )
    assert "2  two" in result and "3  three" in result
    assert "four" not in result


def test_read_file_missing_is_an_error_string(ctx):
    result = execute_tool(ctx, "read_file", {"file_path": "nope.txt"})
    assert result.startswith("Error:")
    assert "not found" in result


def test_read_file_outside_work_dir_is_refused(ctx):
    outside = ctx.work_dir.parent / "secret.txt"
    _write(outside, "secret")
    result = execute_tool(ctx, "read_file", {"file_path": str(outside)})
    assert result.startswith("Error:")
    assert "outside" in result


def test_read_file_missing_argument(ctx):
    result = execute_tool(ctx, "read_file", {})
    assert result.startswith("Error:")


# -------------------------------------------------------------- write_file

def test_write_file_creates_parents_and_file(ctx):
    result = execute_tool(
        ctx,
        "write_file",
        {"file_path": "src/app.js", "content": "console.log('hi');\n"},
    )
    assert result.startswith("Wrote")
    assert (ctx.output_dir / "src" / "app.js").read_text() == "console.log('hi');\n"


def test_write_file_refuses_to_overwrite_non_empty(ctx):
    _write(ctx.output_dir / "app.js", "existing\n")
    result = execute_tool(
        ctx, "write_file", {"file_path": "app.js", "content": "new\n"}
    )
    assert result.startswith("Error:")
    assert (ctx.output_dir / "app.js").read_text() == "existing\n"


def test_write_file_refuses_outside_output_dir(ctx):
    result = execute_tool(
        ctx,
        "write_file",
        {"file_path": str(ctx.work_dir / "evil.js"), "content": "x\n"},
    )
    assert result.startswith("Error:")
    assert "outside" in result


def test_write_file_refuses_oversized_content(ctx):
    result = execute_tool(
        ctx, "write_file", {"file_path": "big.txt", "content": "x" * 60_001}
    )
    assert result.startswith("Error:")
    assert not (ctx.output_dir / "big.txt").exists()


# -------------------------------------------------------------- list_files

def test_list_files_finds_files_and_ignores_node_modules(ctx):
    _write(ctx.work_dir / "a.js", "x")
    _write(ctx.work_dir / "sub" / "b.js", "x")
    _write(ctx.work_dir / "node_modules" / "pkg" / "c.js", "x")
    result = execute_tool(ctx, "list_files", {"pattern": "**/*.js"})
    assert "a.js" in result and os.path.join("sub", "b.js") in result
    assert "node_modules" not in result


def test_list_files_no_match(ctx):
    result = execute_tool(ctx, "list_files", {"pattern": "**/*.zzz"})
    assert "No files matched" in result


# ------------------------------------------------------------- grep_search

def test_grep_search_finds_lines(ctx):
    _write(ctx.work_dir / "a.txt", "hello world\nsecond line\n")
    _write(ctx.work_dir / "b.txt", "say hello again\n")
    result = execute_tool(ctx, "grep_search", {"pattern": "hello"})
    assert "a.txt:1:" in result
    assert "b.txt:1:" in result


def test_grep_search_no_match(ctx):
    _write(ctx.work_dir / "a.txt", "nothing here\n")
    result = execute_tool(ctx, "grep_search", {"pattern": "zzz"})
    assert "No matches" in result


def test_grep_search_bad_pattern_is_an_error(ctx):
    result = execute_tool(ctx, "grep_search", {"pattern": "([bad"})
    assert result.startswith("Error:")


# --------------------------------------------------------------- run_shell

def test_run_shell_reports_exit_code_and_output(ctx):
    result = execute_tool(ctx, "run_shell", {"command": "echo hello"})
    assert "Exit code: 0" in result
    assert "hello" in result


def test_run_shell_blocklist_refuses_rm(ctx):
    result = execute_tool(ctx, "run_shell", {"command": "rm -rf /tmp/x"})
    assert result.startswith("Error:")
    assert "blocklist" in result


def test_run_shell_blocklist_does_not_match_substrings(ctx):
    # "perform" contains "rm" as letters, not as a word. It must run.
    result = execute_tool(ctx, "run_shell", {"command": "echo perform"})
    assert "Exit code: 0" in result


def test_run_shell_asks_for_confirmation_when_not_safe(ctx):
    seen = []
    ctx2 = ToolContext(ctx.work_dir, ctx.output_dir, confirm=lambda cmd: seen.append(cmd) or False)
    result = execute_tool(ctx2, "run_shell", {"command": "echo hello"})
    assert result.startswith("Error:")
    assert "not confirmed" in result
    assert seen == ["echo hello"]


def test_run_shell_safe_command_skips_confirmation(ctx):
    seen = []
    ctx2 = ToolContext(ctx.work_dir, ctx.output_dir, confirm=lambda cmd: seen.append(cmd) or True)
    result = execute_tool(ctx2, "run_shell", {"command": "ls"})
    assert "Exit code: 0" in result
    assert seen == []


def test_run_shell_failing_command_returns_exit_code(ctx):
    result = execute_tool(ctx, "run_shell", {"command": "exit 3"})
    assert "Exit code: 3" in result


def test_run_shell_timeout_kills_the_process_tree(ctx):
    # A child that outlives its shell must not hold the pipes open:
    # the timeout has to reap the whole tree, not just the parent.
    command = '"{}" -c "import time; time.sleep(60)"'.format(sys.executable)
    start = time.monotonic()
    result = execute_tool(ctx, "run_shell", {"command": command, "timeout": 2})
    elapsed = time.monotonic() - start
    assert result.startswith("Error: command timed out after 2 seconds")
    assert elapsed < 20


# ------------------------------------------------------------------ unknown

def test_unknown_tool_is_an_error_string(ctx):
    result = execute_tool(ctx, "teleport", {})
    assert result.startswith("Error:")
    assert "unknown tool" in result


def test_non_dict_arguments_are_an_error_string(ctx):
    result = execute_tool(ctx, "read_file", ["not", "a", "dict"])
    assert result.startswith("Error:")
