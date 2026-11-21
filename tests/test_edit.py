"""Tests for edit_file: zero matches, one match, many matches."""

import os

import pytest

from agent.tools import execute_tool
from agent.tools_impl import ToolContext


@pytest.fixture
def ctx(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    return ToolContext(work, out)


def _write_and_read(ctx, name, text):
    path = ctx.output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    execute_tool(ctx, "read_file", {"file_path": name})
    return path


def test_edit_one_match_replaces_it(ctx):
    path = _write_and_read(ctx, "app.js", "const a = 1;\nconst b = 2;\n")
    result = execute_tool(
        ctx,
        "edit_file",
        {"file_path": "app.js", "old_string": "const a = 1;", "new_string": "const a = 10;"},
    )
    assert result.startswith("Replaced 1 occurrence")
    assert path.read_text() == "const a = 10;\nconst b = 2;\n"


def test_edit_zero_matches_is_an_error_and_changes_nothing(ctx):
    path = _write_and_read(ctx, "app.js", "const a = 1;\n")
    result = execute_tool(
        ctx,
        "edit_file",
        {"file_path": "app.js", "old_string": "const z = 9;", "new_string": "const z = 8;"},
    )
    assert result.startswith("Error:")
    assert "not found" in result
    assert path.read_text() == "const a = 1;\n"


def test_edit_many_matches_is_an_error_without_replace_all(ctx):
    path = _write_and_read(ctx, "app.js", "let x = 1;\nlet x = 2;\n")
    result = execute_tool(
        ctx,
        "edit_file",
        {"file_path": "app.js", "old_string": "let x", "new_string": "let y"},
    )
    assert result.startswith("Error:")
    assert "2 times" in result
    assert path.read_text() == "let x = 1;\nlet x = 2;\n"


def test_edit_many_matches_with_replace_all_replaces_all(ctx):
    path = _write_and_read(ctx, "app.js", "let x = 1;\nlet x = 2;\n")
    result = execute_tool(
        ctx,
        "edit_file",
        {
            "file_path": "app.js",
            "old_string": "let x",
            "new_string": "let y",
            "replace_all": True,
        },
    )
    assert "Replaced 2 occurrence" in result
    assert path.read_text() == "let y = 1;\nlet y = 2;\n"


def test_edit_without_reading_first_is_refused(ctx):
    path = ctx.output_dir / "app.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("const a = 1;\n", encoding="utf-8")
    result = execute_tool(
        ctx,
        "edit_file",
        {"file_path": "app.js", "old_string": "const a = 1;", "new_string": "const a = 2;"},
    )
    assert result.startswith("Error:")
    assert "Read" in result and "first" in result
    assert path.read_text() == "const a = 1;\n"


def test_edit_warns_when_file_changed_since_read(ctx):
    path = _write_and_read(ctx, "app.js", "const a = 1;\n")
    # Change the file behind the agent's back and force a new mtime.
    path.write_text("const a = 5;\n", encoding="utf-8")
    stamp = path.stat().st_mtime + 5
    os.utime(path, (stamp, stamp))
    result = execute_tool(
        ctx,
        "edit_file",
        {"file_path": "app.js", "old_string": "const a = 5;", "new_string": "const a = 6;"},
    )
    assert "Warning" in result
    assert "changed on disk" in result
    assert path.read_text() == "const a = 6;\n"


def test_edit_missing_file_is_an_error(ctx):
    result = execute_tool(
        ctx,
        "edit_file",
        {"file_path": "gone.js", "old_string": "a", "new_string": "b"},
    )
    assert result.startswith("Error:")
    assert "not found" in result
