"""Tests for the $1 budget guard: cost maths and the hard stop."""

from agent.budget import Budget
from agent.loop import run_agent
from conftest import FakeClient, FakeUsage, text_response, tool_call_response


def test_cost_maths_uncached():
    budget = Budget()
    budget.add(FakeUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000))
    # 1M uncached input at $1.32 + 1M output at $3.96 = $5.28.
    assert abs(budget.spent_usd - 5.28) < 1e-9
    assert budget.prompt_tokens == 1_000_000
    assert budget.completion_tokens == 1_000_000


def test_cost_maths_cached_input_is_cheaper():
    budget = Budget()
    budget.add(
        FakeUsage(prompt_tokens=1_000_000, completion_tokens=0, cached_tokens=500_000)
    )
    # 500k uncached at $1.32 + 500k cached at $0.044 = $0.682.
    assert abs(budget.spent_usd - 0.682) < 1e-9
    assert budget.cached_tokens == 500_000


def test_budget_summary_states_dollars_and_tokens():
    budget = Budget()
    budget.add(FakeUsage(prompt_tokens=100, completion_tokens=50))
    text = budget.summary()
    assert "$0.0003" in text
    assert "100 prompt tokens" in text
    assert "50 completion tokens" in text


def test_guard_stops_the_loop_at_the_cap(tmp_path):
    # A tiny cap and fat usage: the first call already blows past it.
    budget = Budget(cap_usd=0.001)
    usage = FakeUsage(prompt_tokens=1000, completion_tokens=1000)
    scripted = [
        tool_call_response(
            [("c1", "write_file", {"file_path": "a.txt", "content": "hello"})],
            usage=usage,
        ),
        tool_call_response(
            [("c2", "write_file", {"file_path": "b.txt", "content": "hello"})],
            usage=usage,
        ),
        text_response("done"),
    ]
    client = FakeClient(scripted)
    result = run_agent(
        {"system": {"name": "Test"}},
        work_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
        api_key="fake",
        budget=budget,
        client=client,
    )
    assert result.status == "budget"
    # Only one model call went out; the loop stopped before the second.
    assert len(client.chat.completions.calls) == 1
    assert result.budget.spent_usd > 0.001
    # Work done before the stop is still on disk.
    assert (tmp_path / "out" / "a.txt").read_text() == "hello"


def test_per_call_max_tokens_is_8000(tmp_path):
    client = FakeClient([text_response("done")])
    run_agent(
        {"system": {"name": "Test"}},
        work_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
        api_key="fake",
        client=client,
    )
    call = client.chat.completions.calls[0]
    assert call["max_tokens"] == 8000
    assert call["model"] == "deepseek-v4-pro"


def test_estimated_full_run_fits_under_one_dollar():
    # The design estimates 30k-60k output tokens for a full generation.
    # At $3.96 per million, 60k output tokens cost about $0.24, and
    # 20k input tokens per turn over 10 turns cost about $0.26.
    output_cost = 60_000 * 3.96 / 1_000_000
    input_cost = 10 * 20_000 * 1.32 / 1_000_000
    assert output_cost + input_cost < 0.90
