"""Message history, token estimation, and simple compaction.

The loop keeps its history as a plain list of OpenAI-format messages:
system, then alternating user and assistant messages, with tool results
as ``role: "tool"`` messages carrying the matching ``tool_call_id``.

Token counts are estimated, never measured by an API call: roughly
four characters per token, two per token for dense JSON. The estimate
only drives the compaction trigger. The budget guard uses the exact
server-reported usage, never this estimate.
"""

from . import config


def estimate_tokens(text, dense_json=False):
    """Rough token count for a string. Cheap and good enough for triggers."""
    if not text:
        return 0
    chars_per_token = 2 if dense_json else 4
    return max(1, len(text) // chars_per_token)


def estimate_messages_tokens(messages):
    """Rough token count for a whole message list."""
    total = 0
    for message in messages:
        content = message.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        total += estimate_tokens(content)
        for call in message.get("tool_calls") or []:
            function = call.get("function", {}) if isinstance(call, dict) else {}
            total += estimate_tokens(function.get("arguments", ""))
    return total


def truncate_result(text, max_chars=config.MAX_TOOL_RESULT_CHARS):
    """Cap one tool result. Keep the head and the tail, note what was cut.

    Both ends are kept because useful information lives at the end of
    files too (latest log lines, end of a stack trace).
    """
    if len(text) <= max_chars:
        return text
    cut = len(text) - max_chars
    half = max_chars // 2
    note = "\n\n[... {} characters cut from the middle ...]\n\n".format(cut)
    return text[:half] + note + text[-half:]


def maybe_compact(messages, summariser):
    """Shrink the history if it passes 85% of the context window.

    ``summariser`` is a callable that takes the message list and returns
    a short summary string (in the real loop it makes one model call).
    The summary replaces the middle of the history; the last user message
    is always kept, so the current task is never lost. Returns the new
    message list. If nothing needs compacting, the list is returned
    unchanged.
    """
    limit = int(config.CONTEXT_WINDOW_TOKENS * config.COMPACTION_TRIGGER_FRACTION)
    if estimate_messages_tokens(messages) < limit:
        return messages
    if len(messages) <= 3:
        return messages
    summary = summariser(messages)
    # Keep the system prompt and the last user message; the summary
    # becomes a synthetic user/assistant pair between them.
    system = messages[0]
    last_user = None
    for message in reversed(messages):
        if message.get("role") == "user":
            last_user = message
            break
    compacted = [
        system,
        {"role": "user", "content": "Summary of the conversation so far:\n" + summary},
        {
            "role": "assistant",
            "content": "Understood. Continuing from the summary above.",
        },
    ]
    if last_user is not None:
        compacted.append(last_user)
    return compacted
