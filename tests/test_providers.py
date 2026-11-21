"""Tests for the DeepSeek-only config: one model, one provider.

The agent talks to DeepSeek deepseek-v4-pro through the official
DeepSeek API and nothing else. These tests lock that in: the model
id, the base URL and the key variable, the loop sending the DeepSeek
model, DeepSeek pricing in the budget, and the CLI reading the
DeepSeek key.
"""

import pytest

from agent import config
from agent.budget import Budget
from agent.loop import run_agent
from conftest import FakeClient, FakeUsage, text_response


def test_config_is_deepseek_only():
    assert config.MODEL_ID == "deepseek-v4-pro"
    assert config.BASE_URL == "https://api.deepseek.com"
    assert config.API_KEY_ENV_VAR == "DEEPSEEK_API_KEY"


def test_loop_calls_the_deepseek_model(tmp_path):
    client = FakeClient([text_response("done")])
    run_agent(
        {"system": {"name": "Test"}},
        work_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
        api_key="fake",
        client=client,
    )
    call = client.chat.completions.calls[0]
    assert call["model"] == "deepseek-v4-pro"


def test_budget_charges_deepseek_prices():
    budget = Budget()
    budget.add(
        FakeUsage(prompt_tokens=1000, completion_tokens=1000)
    )
    # 1000 uncached input tokens at $1.32/1M = $0.00132, plus
    # 1000 output tokens at $3.96/1M = $0.00396.
    assert budget.spent_usd == pytest.approx(0.00132 + 0.00396)
    assert budget.prompt_tokens == 1000
    assert budget.completion_tokens == 1000
    assert "Spent $0.0053" in budget.summary()
    assert not budget.exceeded()


def test_budget_counts_cached_input_at_the_cached_price():
    budget = Budget()
    budget.add(
        FakeUsage(prompt_tokens=1000, completion_tokens=0, cached_tokens=1000)
    )
    # 1000 cached input tokens at $0.044/1M = $0.000044.
    assert budget.spent_usd == pytest.approx(0.000044)


def test_run_reports_real_deepseek_cost(tmp_path):
    usage = FakeUsage(prompt_tokens=5000, completion_tokens=8000)
    client = FakeClient([text_response("done", usage=usage)])
    result = run_agent(
        {"system": {"name": "Test"}},
        work_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
        api_key="fake",
        client=client,
    )
    assert result.status == "done"
    # 5000 input at $1.32/1M = $0.0066, 8000 output at $3.96/1M = $0.03168.
    assert result.budget.spent_usd == pytest.approx(0.0066 + 0.03168)


def test_cli_reads_the_deepseek_key(tmp_path, monkeypatch):
    # The CLI takes the key from DEEPSEEK_API_KEY. The loop itself is
    # stubbed out so no network call happens.
    import agent.__main__ as cli
    from agent.loop import AgentResult

    doc = tmp_path / "doc.md"
    view = tmp_path / "view.md"
    doc.write_text("# Doc\n")
    view.write_text("# View\n")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake")
    seen = {}

    def fake_run_agent(*args, **kwargs):
        seen.update(kwargs)
        return AgentResult(status="done", final_text="ok")

    monkeypatch.setattr(cli, "run_agent", fake_run_agent)
    code = cli.main(
        [
            "--doc",
            str(doc),
            "--view",
            str(view),
            "--output",
            str(tmp_path / "out"),
        ]
    )
    assert code == 0
    assert seen["api_key"] == "fake"
    assert "provider" not in seen


def test_cli_missing_key_fails(tmp_path, monkeypatch):
    import agent.__main__ as cli

    doc = tmp_path / "doc.md"
    view = tmp_path / "view.md"
    doc.write_text("# Doc\n")
    view.write_text("# View\n")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    code = cli.main(
        [
            "--doc",
            str(doc),
            "--view",
            str(view),
            "--output",
            str(tmp_path / "out"),
        ]
    )
    assert code == 2
