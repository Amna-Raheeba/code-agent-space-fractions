"""Tests for the agent loop: stop conditions, recovery, retries."""

from agent import context
from agent.loop import run_agent
from conftest import (
    ApiError,
    FakeClient,
    length_response,
    text_response,
    tool_call_response,
)


def _run(scripted, tmp_path, **kwargs):
    client = FakeClient(scripted)
    result = run_agent(
        {"system": {"name": "Test"}},
        work_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
        api_key="fake",
        client=client,
        **kwargs,
    )
    return result, client


def test_loop_ends_when_the_model_stops_calling_tools(tmp_path):
    result, client = _run([text_response("All done.")], tmp_path)
    assert result.status == "done"
    assert result.final_text == "All done."
    assert result.turns == 1
    assert len(client.chat.completions.calls) == 1


def test_loop_stops_at_max_turns(tmp_path):
    scripted = [
        tool_call_response(
            [("c{}".format(i), "write_file", {"file_path": "f{}.txt".format(i), "content": "x"})]
        )
        for i in range(10)
    ]
    result, client = _run(scripted, tmp_path, max_turns=3)
    assert result.status == "max_turns"
    assert result.turns == 3
    assert len(client.chat.completions.calls) == 3


def test_files_written_excludes_dependency_folders(tmp_path):
    out = tmp_path / "out"
    (out / "node_modules" / "pkg").mkdir(parents=True)
    (out / "node_modules" / "pkg" / "index.js").write_text("x")
    (out / ".git").mkdir()
    (out / ".git" / "HEAD").write_text("ref")
    scripted = [
        tool_call_response([("c1", "write_file", {"file_path": "app.js", "content": "x"})]),
        text_response("done"),
    ]
    result, client = _run(scripted, tmp_path)
    assert result.files_written == ["app.js"]


def test_unknown_tool_name_becomes_an_error_result(tmp_path):
    scripted = [
        tool_call_response([("c1", "teleport", {})]),
        text_response("Fixed that."),
    ]
    result, client = _run(scripted, tmp_path)
    assert result.status == "done"
    second_call = client.chat.completions.calls[1]
    tool_results = [
        m for m in second_call["messages"] if m.get("role") == "tool"
    ]
    assert len(tool_results) == 1
    assert "unknown tool" in tool_results[0]["content"]


def test_bad_json_arguments_become_an_error_result(tmp_path):
    from conftest import FakeMessage, FakeResponse, FakeToolCall

    bad_call = FakeToolCall("c1", "read_file", "{not json")
    scripted = [
        FakeResponse(FakeMessage(content=None, tool_calls=[bad_call]), finish_reason="tool_calls"),
        text_response("Recovered."),
    ]
    result, client = _run(scripted, tmp_path)
    assert result.status == "done"
    second_call = client.chat.completions.calls[1]
    tool_results = [
        m for m in second_call["messages"] if m.get("role") == "tool"
    ]
    assert "not valid JSON" in tool_results[0]["content"]


def test_length_finish_reason_asks_the_model_to_continue(tmp_path):
    scripted = [length_response(), text_response("Finished after continuing.")]
    result, client = _run(scripted, tmp_path)
    assert result.status == "done"
    assert result.final_text == "Finished after continuing."
    second_call = client.chat.completions.calls[1]
    assert any(
        m.get("role") == "user" and "token limit hit" in (m.get("content") or "")
        for m in second_call["messages"]
    )


def test_length_with_tool_calls_answers_them_before_continuing(tmp_path):
    # Regression: a reply cut off at the output limit can still carry
    # tool calls. Those calls must be answered with tool messages before
    # the continuation is appended, or the API rejects the next request
    # ("insufficient tool messages following tool_calls message").
    from conftest import FakeMessage, FakeResponse, FakeToolCall

    cut_call = FakeToolCall("c1", "list_files", "{}")
    scripted = [
        FakeResponse(
            FakeMessage(content=None, tool_calls=[cut_call]),
            finish_reason="length",
        ),
        text_response("Finished after continuing."),
    ]
    result, client = _run(scripted, tmp_path)
    assert result.status == "done"
    second_call = client.chat.completions.calls[1]
    tool_results = [
        m for m in second_call["messages"] if m.get("role") == "tool"
    ]
    assert len(tool_results) == 1
    assert tool_results[0]["tool_call_id"] == "c1"


def test_transient_api_error_is_retried_then_succeeds(tmp_path):
    scripted = [
        ApiError(429, "rate limited"),
        ApiError(503, "overloaded"),
        text_response("Done after retries."),
    ]
    result, client = _run(scripted, tmp_path, sleep_fn=lambda seconds: None)
    assert result.status == "done"
    assert len(client.chat.completions.calls) == 3


def test_bad_key_stops_at_once_without_retry(tmp_path):
    scripted = [ApiError(401, "bad key")]
    result, client = _run(scripted, tmp_path, sleep_fn=lambda seconds: None)
    assert result.status == "error"
    assert len(client.chat.completions.calls) == 1


def test_stop_event_breaks_the_loop_cleanly(tmp_path):
    import threading

    stop = threading.Event()
    stop.set()
    scripted = [text_response("never reached")]
    result, _ = _run(scripted, tmp_path, stop_event=stop)
    assert result.status == "stopped"
    assert result.turns == 0


def test_maybe_compact_keeps_system_and_last_user_message(monkeypatch):
    monkeypatch.setattr(context.config, "CONTEXT_WINDOW_TOKENS", 1000)
    monkeypatch.setattr(context.config, "COMPACTION_TRIGGER_FRACTION", 0.85)
    messages = [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": "Build the project."},
        {"role": "assistant", "content": "x" * 2000},
        {"role": "user", "content": "Now add tests."},
        {"role": "assistant", "content": "y" * 2000},
        {"role": "user", "content": "Keep going."},
    ]
    compacted = context.maybe_compact(messages, lambda msgs: "SUMMARY")
    assert compacted[0] == messages[0]
    assert compacted[-1] == messages[-1]
    assert "SUMMARY" in compacted[1]["content"]
    assert len(compacted) < len(messages)


def test_maybe_compact_leaves_small_histories_alone():
    messages = [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": "Hi."},
    ]
    assert context.maybe_compact(messages, lambda msgs: "SUMMARY") == messages
