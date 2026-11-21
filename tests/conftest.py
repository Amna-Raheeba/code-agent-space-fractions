"""Shared fake DeepSeek client for the unit tests.

The fakes mimic the shape of the ``openai`` package's response
objects (choices[0].message, tool_calls, finish_reason, usage) so the
loop can run end to end without any network call. No test in this
suite ever touches api.deepseek.com.
"""

import json
from types import SimpleNamespace


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments  # JSON string, like the real API


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class FakeUsage:
    def __init__(self, prompt_tokens=100, completion_tokens=50, cached_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.prompt_tokens_details = SimpleNamespace(cached_tokens=cached_tokens)


class FakeResponse:
    def __init__(self, message, finish_reason="stop", usage=None):
        self.choices = [FakeChoice(message, finish_reason)]
        self.usage = usage if usage is not None else FakeUsage()


class FakeCompletions:
    """Returns scripted responses in order; records every call."""

    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._scripted:
            raise AssertionError("Fake client ran out of scripted responses")
        item = self._scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClient:
    def __init__(self, scripted):
        self.chat = SimpleNamespace(completions=FakeCompletions(scripted))


class ApiError(Exception):
    """An API failure carrying an HTTP status, like openai.APIStatusError."""

    def __init__(self, status_code, message="api error"):
        super().__init__(message)
        self.status_code = status_code


def text_response(text, usage=None):
    return FakeResponse(FakeMessage(content=text), finish_reason="stop", usage=usage)


def tool_call_response(calls, usage=None):
    """calls: list of (id, tool name, arguments dict)."""
    tool_calls = [
        FakeToolCall(call_id, name, json.dumps(args)) for call_id, name, args in calls
    ]
    return FakeResponse(
        FakeMessage(content=None, tool_calls=tool_calls),
        finish_reason="tool_calls",
        usage=usage,
    )


def length_response(usage=None):
    """A reply cut off by the output token limit."""
    return FakeResponse(
        FakeMessage(content="half a file..."), finish_reason="length", usage=usage
    )
