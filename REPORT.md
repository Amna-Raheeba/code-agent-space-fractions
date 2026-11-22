# Task 1 — Project Report

**Amna Raheeba** — submission for Prof. Peng Liang's evaluation task, Wuhan University.

## 1. The task as I understood it

Study how open-source Claude Code implementations work, then build a simplified Code Agent of my own. The agent takes the two Space Fractions architecture documents as input and writes the whole project they describe. The agent itself must be a Windows desktop application (.exe, double-click run, no Python install needed) with a small window for the API key, the input files, the task and the output folder. The model is DeepSeek's deepseek-v4-pro through the official API, and one generation run must stay within $1 of token cost.

## 2. What I studied first

I read the three reference repositories before writing any code:

- **anthropics/claude-code** — the public repo holds documentation and plugins, not the CLI source. The internals have to be learned from the community deep dive below.
- **Windy3f3f3f3f/how-claude-code-works** — the useful source: the agent is one loop. The model answers with text (finished) or with tool calls; tool results go back into the conversation; the loop repeats. Around that loop sit context management, retries, and sub-agents — in that order of importance.
- **ultraworkers/claw-code** — a museum exhibit built by an agent, interesting to look at but not a design reference. A minimal from-scratch clone (~13 tools) was the better size guide; I took a six-tool core.

## 3. My design

- **Language and window:** Python 3.11 with a tkinter GUI — no heavy dependencies, and PyInstaller turns it into a single Windows .exe.
- **Six tools only:** read_file, write_file, edit_file, list_files, grep_search, run_shell. Everything the task needs, nothing extra.
- **Deterministic preprocessing:** the two documents are first converted to a structured JSON spec (components, APIs, data models, requirements, diagrams) by a normal parser, not by the model. The spec carries an `input_gaps` field that records what the documents fail to state. The real spec for these documents is in `example/spec.json`.
- **Budget guard:** every model call's cost is priced from the usage the server reports (never estimated), at DeepSeek's published prices ($1.32 / $0.044 cached / $3.96 per million tokens, peak). The run stops itself at $0.90, and at 40 turns.
- **Build:** PyInstaller cannot make a Windows .exe on Linux, so GitHub Actions builds it on a Windows runner on every push — unit tests first, then the .exe as a downloadable artifact.

## 4. The thinking-mode finding

DeepSeek turns thinking mode on by default at high effort. With tools attached, a request must return the model's `reasoning_content` on the next turn or the API rejects it with a 400 — and thinking tokens are billed as output while adding nothing to a code-generation run. My agent disables thinking (`"thinking": {"type": "disabled"}`) in both of its call sites. I verified this live: with thinking disabled, no `reasoning_content` is produced, tool calling works, and the second turn succeeds.

## 5. How I verified the work

- **58 unit tests** for the agent (mocked model client): the loop, the tools, the budget guard, the preprocessor, error handling. All pass locally and in CI. One regression test covers a reply cut off at the output limit while carrying tool calls: the calls are answered before the model is asked to continue, which the API requires.
- **CI on windows-latest:** the same tests, then the .exe build. The artifact `code-agent-windows` is attached to the Actions run.
- **Live tests on the real API:** a plain call, a tool call, and a second turn carrying the tool result — all succeed, and the account's usage object matches what my budget guard records.
- **The generated game:** 46 Jest tests pass (7 suites), I ran its services and played it end to end over HTTP — add a question, list questions, check an answer, start a game, read the score, end the game — and the desktop version was played in its window from the intro screen to the final score.

## 6. What it really cost (server-reported usage)

| Run | Turns / calls | Cost |
|---|---|---|
| Connectivity + tool-calling tests | 3 calls | ≈ $0.0006 |
| Dry run (package.json + one source file) | 7 | $0.0227 |
| **Full Space Fractions generation** | **24** | **$0.1337** |
| **Desktop (Electron) client generation** | **40 calls** | **$0.1725** |
| **Total** | | **≈ $0.33** |

The task limit is $1. The full generation used 528,905 prompt tokens (520,832 of them cache hits, which is why the cost stays low) and 25,283 completion tokens.

## 7. The generated project

The agent's real output is included in `example-output/`: three components (Game, Question, User) plus shared modules, SQL DDL, an OpenAPI file, the proto definition, a Dockerfile and docker-compose, and tests. Two section-L deliverables were added in a short follow-up run on the same folder: the Kubernetes manifest (`k8s/spacefractions-deployment.yaml`) and `traceability_matrix.csv`, which carries exactly the three mappings the document gives (FR-1, NFR-1, ASR-1). Its own README maps every use case in the diagrams to the endpoint that implements it, and lists what the documents left open. The endpoints and tables the documents do not define (questions, scores, login, admin updates) were designed from the diagrams and are labelled as designed, not specified.

A later run added a desktop version of the game to the same output: an Electron application (`example-output/desktop/`) that starts the Game, Question and User services itself, so `npm run desktop` launches everything. Its window follows the documented use cases - intro screen, main menu (Play, View Score, Help), fraction questions with clickable answers and feedback, and an ending screen showing the score - and it plays over HTTP against the running services. Because the documents define no questions and no correct-answer field, the desktop app ships a seed bank of 12 fraction questions with a correct-answer index, labelled as designed in its README; it seeds the Question service at launch, matches the served questions to the bank by prompt, and keeps the score tally, while the Game service still runs the game lifecycle. The generated project's tests now number 46 across 7 suites.

## 8. Honest limitations

- The architecture documents map only 3 requirements, leave the test matrix empty, and use sequence-diagram syntax in the Object diagram. My preprocessor records these gaps instead of inventing requirements.
- The generated question bank starts empty; questions are added through the admin endpoints. The desktop client ships its own designed seed bank of 12 questions and seeds the service at launch.
- The spec defines no "correct answer" field for a question, so the services' answer checking validates the chosen option's bounds; right/wrong judgement exists only in the desktop client's designed seed bank, not in the services.
- OAuth2 in the generated project is a stub with an injectable verifier, and the 1,000-concurrent-user assumption is stated in the documents but was not load-tested.

## 9. How to run it

Download the .exe from the repo's Actions run, double-click it, enter a DeepSeek API key, choose the two documents and an output folder, and press Run. From source: `pip install -r requirements.txt`, then `python -m agent --doc Architecture_Documentation.md --view Architecture_View.md --output ./space-fractions` with `DEEPSEEK_API_KEY` set. The key is never stored in the repo and never baked into the .exe.
