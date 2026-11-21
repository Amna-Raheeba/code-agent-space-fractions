"""Static configuration for the Code Agent.

Nothing secret lives in this file. The API key is supplied at runtime
(GUI field or environment variable) and never written here. Prices
are from DeepSeek's public pricing page as of November 2026; confirm
them there before the first real run.
"""

# One model, one provider: official DeepSeek, exactly as Prof. Liang
# asked. deepseek-v4-pro through api.deepseek.com. Nothing else is
# supported — there are no other providers in this project.
MODEL_ID = "deepseek-v4-pro"
BASE_URL = "https://api.deepseek.com"
API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"

# Loop limits.
MAX_TURNS = 40
MAX_TOKENS_PER_CALL = 8000
MAX_CONTINUATION_RETRIES = 3
MAX_API_RETRIES = 3

# Money. The task requires the whole generation to cost under $1.
# The loop stops at $0.90 so a call already in flight cannot push it over.
BUDGET_CAP_USD = 0.90

# Prices in US dollars per million tokens.
PRICE_INPUT_PER_MILLION = 1.32
PRICE_CACHED_INPUT_PER_MILLION = 0.044
PRICE_OUTPUT_PER_MILLION = 3.96

# Tool result limits.
MAX_TOOL_RESULT_CHARS = 50_000
MAX_FILE_WRITE_CHARS = 60_000
MAX_LIST_LINES = 200
MAX_GREP_LINES = 100
SHELL_OUTPUT_MAX_BYTES = 5 * 1024 * 1024
SHELL_TIMEOUT_SECONDS = 30

# Context window of deepseek-v4-pro and the compaction trigger.
CONTEXT_WINDOW_TOKENS = 1_000_000
COMPACTION_TRIGGER_FRACTION = 0.85
