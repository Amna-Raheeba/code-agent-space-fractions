# Code Agent

A small coding agent in the style of Claude Code. You give it two
architecture documents, and it writes the whole software project
described in them: source files, the dependency manifest, a README,
and tests. It runs the tests and fixes what fails, then stops.

The model behind it is DeepSeek's deepseek-v4-pro by default,
called through the official DeepSeek API. The agent works in a loop:
it sends the task to the model, the model calls tools (read a file,
write a file, edit a file, list files, search, run a command), the
results go back to the model, and the loop repeats until the model
stops calling tools. A run is capped at 40 turns and at $0.90 of
DeepSeek usage, so a full generation stays under $1. The exact spend
is shown live and printed at the end.

## What it was built for

Prof. Peng Liang's Task 1 (Wuhan University, November 2026): build a
simplified Code Agent, then use it to generate the Space Fractions
game from its architecture documents. The agent itself is the desktop
application in this project. It ships as a Windows .exe you
double-click; no Python install is needed on the machine that runs it.

## Run it

The agent runs on one model only: DeepSeek's `deepseek-v4-pro`
through the official DeepSeek API at api.deepseek.com. That is what
the task asks for, and there is no other provider to pick.

Get a key at platform.deepseek.com: create an account, create an
API key, and add a small top-up. The key is entered in the app and
never stored in the repo, never baked into the .exe, and never
written to any file.

From source, on any machine with Python 3.11 or newer:

```console
pip install -r requirements.txt
python -m agent --doc Architecture_Documentation.md --view Architecture_View.md --output ./space-fractions
```

The key comes from the `DEEPSEEK_API_KEY` environment variable, or
pass `--api-key`. The generated project lands in the output folder.

On Windows, the simplest way is the .exe from the GitHub Actions
build (see below). Double-click it, fill in your DeepSeek key, pick
the two documents and an output folder, and press Run.

## What it costs

DeepSeek's published prices at the time of writing are about $1.32
per million uncached input tokens and $3.96 per million output
tokens. A full game generation is roughly 30,000 to 60,000 output
tokens, which works out to about $0.15 to $0.35. The agent stops
itself at $0.90, so it cannot cross $1 even if the last call is
already running. Confirm the prices on DeepSeek's pricing page
before a big run; if they change, update the numbers in
`agent/config.py`.

Live runs are now recorded, not estimated. A dry run (package.json
and one source file) cost $0.0227 of server-reported usage. The full
Space Fractions generation — 24 turns, the complete project in
`example-output/` — cost $0.1337. Both are far under the $1 task
limit, and the $0.90 cap was never approached. See REPORT.md for the
full record, including the thinking-mode fix the live runs required.

Two deliverables from section L of the architecture document were
not part of that first generation: the Kubernetes manifest
(`example-output/k8s/spacefractions-deployment.yaml`) and the
traceability matrix (`example-output/traceability_matrix.csv`).
They were added afterwards in a short follow-up run on the same
output folder; no other file was changed. The matrix contains
exactly the three mappings the document itself gives (FR-1, NFR-1,
ASR-1) - the document traces no others.

A further run on the same folder added a desktop version of the
game: an Electron application in `example-output/desktop/` that
starts the three services itself and plays the game in a native
window (intro screen, main menu, fraction questions with feedback,
ending screen with the score), talking to the services over HTTP.
That run cost $0.1725 and is the run shown in the demo video. The
desktop app ships a seed bank of 12 fraction questions with a
correct-answer index, labelled in its README as designed - the
documents define no questions and no correct-answer field. Launch
it with `npm run desktop`. The generated project's tests now
number 46 across 7 suites, including the desktop client's.

## How the .exe is built

PyInstaller cannot build a Windows .exe from Linux, so the build
happens on a Windows runner in GitHub Actions
(`.github/workflows/build-windows.yml`). Every push runs the unit
tests, then builds the .exe and uploads it as a build artifact.
Download it from the Actions run, double-click, and it just works.

## The input documents, honestly

The Space Fractions architecture documents the agent reads are thin
in places. The traceability table maps only three requirements, the
test matrix in the document is empty, and the Object diagram uses
sequence-diagram syntax. The agent records these gaps in its input
JSON and lists them in the generated README instead of inventing
requirements the documents never stated. If the documents improve,
the generated project improves with them.

## Layout

```text
agent/          the loop, the six tools, the budget guard, the preprocessor
gui/app.py      the tkinter window (same loop, no separate code path)
tests/          unit tests with a mocked DeepSeek client
requirements.txt
code-agent.spec PyInstaller spec for the Windows .exe
REPORT.md       the task report: design, verification, and real recorded costs
example/        the structured JSON the preprocessor makes from the documents
example-output/ the Space Fractions project from the real generation run,
                including the Electron desktop game in desktop/
```
