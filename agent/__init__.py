"""Code Agent: a simplified Claude-Code-style agent on DeepSeek.

Reads two architecture documents, generates a complete software
project from them, and keeps the whole run under $1 of DeepSeek usage.
"""

from .budget import Budget
from .loop import AgentResult, run_agent
from .preprocess import preprocess, spec_to_json

__version__ = "0.1.0"

__all__ = [
    "AgentResult",
    "Budget",
    "preprocess",
    "run_agent",
    "spec_to_json",
    "__version__",
]
