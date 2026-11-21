"""The agent loop. One loop, six tools, no extras.

The loop sends the task to DeepSeek, DeepSeek answers either with
plain text (done) or with tool calls (do this, then come back). Each
tool result goes back to the model. The loop repeats until the model
stops calling tools, or 40 turns pass, or the $0.90 budget cap is hit,
or the user presses Stop.

Errors are never crashes. A failed tool call comes back as a result
marked as an error, and the model usually fixes its own mistake on
the next turn.
"""

import json
import random
import time
from dataclasses import dataclass, field

from . import config
from .budget import Budget
from .context import maybe_compact
from .prompt import build_system_prompt, continuation_message, task_message
from .tools import TOOL_SCHEMAS, execute_tool
from .tools_impl import ToolContext

# HTTP statuses worth retrying: rate limit and server overload.
RETRYABLE_STATUS = (429, 503, 529)
# Statuses that will never succeed on retry: bad request, bad key.
FATAL_STATUS = (400, 401)


@dataclass
class AgentResult:
    """What a run produced, in one place for the CLI and the GUI."""

    status: str  # done | budget | max_turns | error | stopped
    final_text: str = ""
    turns: int = 0
    budget: Budget = field(default_factory=Budget)
    files_written: list = field(default_factory=list)


def run_agent(
    task_input,
    work_dir,
    output_dir,
    api_key,
    budget=None,
    on_event=None,
    client=None,
    confirm=None,
    max_turns=config.MAX_TURNS,
    stop_event=None,
    sleep_fn=None,
    extra_instructions=None,
):
    """Run the agent loop. Returns an AgentResult.

    The model is always DeepSeek deepseek-v4-pro through the official
    API (``config.MODEL_ID`` / ``config.BASE_URL``). There is no other
    provider. ``client`` is an already-built OpenAI-compatible client;
    when it is None one is created from ``api_key``. Tests inject a
    fake client.
    ``on_event`` is called as on_event(kind, text) with kinds "call",
    "tool", "cost", "done", "error", "info".
    """
    sleep_fn = sleep_fn or time.sleep
    budget = budget if budget is not None else Budget()
    spec = task_input
    if isinstance(spec, str):
        spec = json.loads(spec)
    ctx = ToolContext(work_dir, output_dir, confirm=confirm)

    if client is None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=config.BASE_URL)
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            return AgentResult(
                status="error",
                final_text="Could not create the DeepSeek client: {}".format(exc),
                budget=budget,
            )

    messages = [
        {"role": "system", "content": build_system_prompt(work_dir)},
        {"role": "user", "content": task_message(spec, extra_instructions)},
    ]
    turns = 0
    length_retries = 0

    def emit(kind, text):
        if on_event is not None:
            on_event(kind, text)

    emit(
        "info",
        "Model: {} (DeepSeek official API, {})".format(
            config.MODEL_ID, config.BASE_URL
        ),
    )

    while turns < max_turns:
        if stop_event is not None and stop_event.is_set():
            return _finish("stopped", "Stopped by the user.", turns, budget, ctx)
        if budget.exceeded():
            return _finish(
                "budget",
                "Budget cap reached ({}). Work done so far is saved in "
                "the output folder.".format(budget.summary()),
                turns,
                budget,
                ctx,
            )
        turns += 1
        emit("call", "Turn {}: calling the model...".format(turns))
        try:
            response = _call_model_with_retry(
                client, messages, model=config.MODEL_ID, sleep_fn=sleep_fn
            )
        except Exception as exc:  # noqa: BLE001 - API failure ends the run cleanly
            return _finish(
                "error",
                "The model call failed and will not succeed on retry: {}".format(exc),
                turns,
                budget,
                ctx,
            )
        budget.add(getattr(response, "usage", None))
        emit("cost", budget.summary())

        choice = response.choices[0]
        message = choice.message
        finish_reason = getattr(choice, "finish_reason", None)
        tool_calls = list(getattr(message, "tool_calls", None) or [])
        messages.append(_assistant_message(message, tool_calls))

        # The reply was cut off mid-generation: ask the model to pick up
        # where it stopped. Checked before the no-tool-calls test, so a
        # truncated reply is never mistaken for a finished one.
        if finish_reason == "length":
            length_retries += 1
            if length_retries > config.MAX_CONTINUATION_RETRIES:
                return _finish(
                    "error",
                    "The model kept hitting the output token limit. "
                    "Stopping so the run does not burn the budget.",
                    turns,
                    budget,
                    ctx,
                )
            messages.append(continuation_message())
            emit("info", "Reply was cut off; asking the model to continue.")
            continue
        length_retries = 0

        if not tool_calls:
            return _finish(
                "done", getattr(message, "content", "") or "", turns, budget, ctx
            )

        for call in tool_calls:
            if stop_event is not None and stop_event.is_set():
                return _finish("stopped", "Stopped by the user.", turns, budget, ctx)
            name = call.function.name
            arguments = _parse_arguments(call)
            emit("tool", "Tool: {} {}".format(name, _short_args(arguments)))
            if isinstance(arguments, str):
                # _parse_arguments returns an error string on bad JSON.
                result = arguments
            else:
                result = execute_tool(ctx, name, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                }
            )
            emit("tool_result", result[:500])

        # Compaction is a safety net, not a requirement: if the summary
        # call fails, keep going with the history as it is.
        try:
            messages = maybe_compact(
                messages,
                lambda msgs: _summarise(client, msgs, config.MODEL_ID),
            )
        except Exception:  # noqa: BLE001 - compaction must never kill a run
            pass

    return _finish(
        "max_turns",
        "Stopped after {} turns without finishing. Work done so far is "
        "saved in the output folder.".format(max_turns),
        turns,
        budget,
        ctx,
    )


def _finish(status, final_text, turns, budget, ctx):
    # Count project files only: npm install and friends fill the output
    # folder with dependency files that the agent never wrote.
    excluded = {"node_modules", ".git", ".venv", "venv", "__pycache__", ".pytest_cache"}
    files = []
    for path in ctx.output_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ctx.output_dir)
        if excluded.intersection(rel.parts):
            continue
        files.append(str(rel))
    files.sort()
    return AgentResult(
        status=status,
        final_text=final_text,
        turns=turns,
        budget=budget,
        files_written=files,
    )


def _assistant_message(message, tool_calls):
    """An assistant message as a plain dict, safe to send back."""
    data = {"role": "assistant", "content": getattr(message, "content", None) or ""}
    if tool_calls:
        data["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in tool_calls
        ]
    return data


def _parse_arguments(call):
    """Parse a tool call's JSON arguments. An error string on bad JSON."""
    raw = call.function.arguments or "{}"
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return (
            "Error: the arguments for {} were not valid JSON. "
            "Send the arguments again as a JSON object.".format(call.function.name)
        )
    if not isinstance(parsed, dict):
        return "Error: tool arguments must be a JSON object."
    return parsed


def _short_args(arguments):
    if isinstance(arguments, str):
        return ""
    text = json.dumps(arguments)
    return text if len(text) <= 120 else text[:117] + "..."


def _call_model_with_retry(client, messages, model, sleep_fn=time.sleep):
    """One model call, with retries for rate limits and overload only."""
    delay = 1.0
    last_error = None
    for attempt in range(config.MAX_API_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                max_tokens=config.MAX_TOKENS_PER_CALL,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as exc:  # noqa: BLE001 - status decides retry or stop
            last_error = exc
            status = getattr(exc, "status_code", None)
            if status in FATAL_STATUS:
                raise
            if status is not None and status not in RETRYABLE_STATUS:
                raise
            if attempt >= config.MAX_API_RETRIES:
                raise
            sleep_fn(delay + random.uniform(0, 0.5))
            delay = min(delay * 2, 30.0)
    raise last_error


def _summarise(client, messages, model):
    """One short model call that summarises the conversation so far."""
    text = "\n\n".join(
        "{}: {}".format(
            message.get("role", ""),
            message.get("content", "") or "[tool calls]",
        )
        for message in messages
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarise this conversation so far. Preserve key "
                    "decisions, file paths, and what is still to do."
                ),
            },
            {"role": "user", "content": text},
        ],
        max_tokens=2000,
        stream=False,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return response.choices[0].message.content or ""
