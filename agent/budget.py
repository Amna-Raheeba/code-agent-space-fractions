"""Dollar tracking for the $1 budget guard.

Every API response reports how many tokens it used. This module turns
those server-reported numbers into dollars and stops the loop before
it can spend past the cap. It never estimates: the guard only trusts
the usage object the API sends back.
"""

from . import config


class Budget:
    """Running totals for one agent run, priced at DeepSeek's rates."""

    def __init__(self, cap_usd=config.BUDGET_CAP_USD):
        self.cap_usd = cap_usd
        self.prompt_tokens = 0
        self.cached_tokens = 0
        self.completion_tokens = 0
        self.spent_usd = 0.0
        self.calls = 0

    def add(self, usage):
        """Add one API response's usage object (or dict) to the totals.

        ``usage`` may be an OpenAI usage object or a plain dict with
        ``prompt_tokens`` and ``completion_tokens`` keys. Cached input
        tokens are read from ``prompt_tokens_details.cached_tokens``
        when the server reports them; otherwise all prompt tokens are
        charged at the uncached price.
        """
        if usage is None:
            return
        prompt = _get(usage, "prompt_tokens", 0) or 0
        completion = _get(usage, "completion_tokens", 0) or 0
        details = _get(usage, "prompt_tokens_details", None)
        cached = 0
        if details is not None:
            cached = _get(details, "cached_tokens", 0) or 0
        cached = min(cached, prompt)
        uncached = prompt - cached
        cost = (
            uncached * config.PRICE_INPUT_PER_MILLION / 1_000_000
            + cached * config.PRICE_CACHED_INPUT_PER_MILLION / 1_000_000
            + completion * config.PRICE_OUTPUT_PER_MILLION / 1_000_000
        )
        self.prompt_tokens += prompt
        self.cached_tokens += cached
        self.completion_tokens += completion
        self.spent_usd += cost
        self.calls += 1

    def exceeded(self):
        """True once the running total has reached the cap."""
        return self.spent_usd >= self.cap_usd

    def summary(self):
        """One-line human-readable state, for the GUI and the final report."""
        return (
            "Spent ${:.4f} of ${:.2f} cap "
            "({} prompt tokens, {} cached, {} completion tokens, {} calls)".format(
                self.spent_usd,
                self.cap_usd,
                self.prompt_tokens,
                self.cached_tokens,
                self.completion_tokens,
                self.calls,
            )
        )


def _get(obj, name, default=None):
    """Read an attribute from an object or a key from a dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
