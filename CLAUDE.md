# cldx — project context for Claude Code

This file gives Claude Code (and any other LLM agent working in this repo) the project-specific context it needs to make good edits. **Read this first** before opening a non-trivial PR.

If you're a human contributor, see [`CONTRIBUTING.md`](./CONTRIBUTING.md) instead. If you're an LLM agent, also read the *"Contributing as an LLM agent"* section of `CONTRIBUTING.md` — it lists rules that override anything you'd infer from this file.

---

## What cldx is

cldx is a second-layer terminal that wraps [Claude Code](https://docs.claude.com/en/docs/claude-code). It does two things:

1. **Auto-approves safe tool calls** so you stop clicking *"Do you want to proceed?"* dozens of times per task. A configurable policy decides when to auto-yes / auto-no / wait / escalate.
2. **Bridges approval prompts and completion summaries to Telegram** so you can supervise Claude from your phone.

The codebase is small and pragmatic — Python 3.11+, ~5k lines, ~540 tests. No async framework beyond `asyncio`; no DI container; no plugins system beyond pluggable LLM backends.

---

## Architecture in one paragraph

A single `cldx` process attaches to one tmux pane running Claude Code. The `TmuxMonitor` polls that pane once a second (`tmux capture-pane`), the `PromptClassifier` looks at the snapshot and decides the state (approval / running / complete / idle), the `PolicyEngine` decides what to do (auto-yes / wait / escalate), and the `BridgeUI` orchestrates: prints panels, runs the wait-bar, sends keys back to tmux, and forwards approvals/completions to Telegram if configured. There are no background daemons and no shared state — one process per Claude pane, Ctrl-D kills it.

---

## Module map

| File | What it does |
|---|---|
| `cldx/cli.py` | The `BridgeUI` orchestrator + argparse entry point. Most of the runtime lives here. |
| `cldx/tmux_monitor.py` | `tmux capture-pane` polling loop. Strips ANSI for classification but preserves it for the mirror panel. |
| `cldx/prompt_classifier.py` | Decides the pane state. **Anchors on the last `⏺` bullet** — see "Structural classifier" below. |
| `cldx/conversation.py` | Structural extractors: `extract_assistant_step`, `extract_final_message`, `extract_pending_approval`. |
| `cldx/policy_engine.py` | Loads `policy.yml`, applies the active profile, returns `AUTO_YES / AUTO_NO / WAIT_LOCAL / ESCALATE_TELEGRAM`. |
| `cldx/tool_call.py` | Typed `ToolCall` / `ToolResult`, `parse_tool_call` (strict, single-line), `pane_has_tool_call` (loose, multi-line). |
| `cldx/session_picker.py` | Discovers tmux panes; handles "no tmux server" / missing-binary gracefully. |
| `cldx/session_limit.py` | Parses Claude's *"You've hit your session limit · resets HH:MM"* banner. |
| `cldx/startup.py` | Banner + arrow-key session picker; spawns a new tmux+claude session on request. |
| `cldx/telegram_bridge.py` | Two-way Telegram bot — sends approval cards, receives `y/n/1/2/3/free text`. |
| `cldx/telegram_sanitize.py` | Strips box-drawing chars / banner art / ANSI from text before sending to Telegram. |
| `cldx/summarizer.py` | LLM-driven summarisation of the result for Telegram. Backends: Anthropic / Bedrock / Gemini / disabled. |
| `cldx/memory.py` | `~/.cldx/state.yml` — agent name, last-session info, yolo-learned patterns. |
| `cldx/interaction_log.py` | Plain-text per-session log at `~/.cldx/logs/<date>/`. `tail -f` friendly. |
| `cldx/session_store.py` | JSONL event log at `~/.cldx/sessions/<profile>/`. Machine-replayable. |
| `cldx/setup_wizard.py` | Interactive setup flows for LLM backends + Telegram. |

User state lives under `~/.cldx/` (override with `CLDX_HOME`). Defaults are bundled in `cldx/defaults/`.

---

## Structural classifier (the core invariant)

This is the single most important concept in the codebase. Read it before editing `prompt_classifier.py`, `conversation.py`, or the mirror logic in `cli.py`.

Every Claude Code response begins with a `⏺` bullet (U+23FA). When `cldx` decides what the current pane state is, it does NOT use a line-count tail. Instead:

1. Walk up from the bottom of the snapshot to find the **last `⏺` bullet**.
2. The slice `[last_⏺ : end]` is the **state region** — what Claude is showing right now.
3. Pattern-match within that slice:
   - `❯ N. Yes` / numbered options → `APPROVAL_MENU`
   - `Do you want…?` / `(y/n)` → `APPROVAL_YN`
   - `✻ <verb> for <time>` → `COMPLETE`
   - `esc to interrupt` → `RUNNING`
   - Else → `IDLE`

The same anchor drives `extract_final_message` (last `⏺` block → user-visible result), the live mirror (shows from last `⏺` to end), and `_pane_has_tool_calls` (loose tool-call detection over the slice).

**Why it matters:** earlier versions used line-count tails (20, 80, 200) and kept losing edge cases — long file previews pushed menus past the tail, multi-paragraph summaries pushed `✻` past the tail, wrapped diff lines doubled the line count. The structural anchor is invariant under all of those.

**Rules when editing:**
- Don't reintroduce hardcoded tail-line scans for primary classification. `tail_lines` / `completion_tail_lines` / `mirror_lines` remain as *fallbacks* and *minimums*, never as the only window.
- If you add a new state pattern to `policy.yml`, the classifier will scan it inside the same slice — no extra plumbing needed.

---

## Conventions

### Code style

- Python 3.11+. Type hints where they help (function signatures, dataclasses). No `from __future__ import annotations` cleanup commits — leave the existing pattern alone.
- Module-level docstring on every file. Public functions get docstrings; internal helpers usually don't need them unless the *why* is non-obvious.
- 4-space indents, double-quote strings, no trailing whitespace.
- Don't use `print()` for runtime output — use the bridge's `console.print(...)` (Rich) or the existing `interaction_log` / `store.log_event` helpers.
- No bare `except:`. `except SpecificError as e:` only.
- `assert` is for invariants we don't expect to fail at runtime, not user-input validation.

### Comments

- Default to writing no comments. Code that reads cleanly doesn't need them.
- Add a comment only when the *why* is non-obvious — a workaround for a Claude Code UI quirk, a subtle ordering constraint, a regression we already burned ourselves on.
- Never write comments that just describe what the next line does.

### Error handling

- At system boundaries (subprocess, tmux, Telegram API, LLM API) — catch the specific exception, log it via `interaction_log`, raise a domain error (`SessionPickerError`, `TmuxMonitorError`, etc.).
- Inside cldx-to-cldx code — let exceptions propagate. Don't add try/except just to log and re-raise.
- Don't swallow `KeyboardInterrupt` / `EOFError` outside the top-level CLI handler.

### Tests

- All tests under `tests/`. Unit tests in `tests/unit/`, integration in `tests/integration/`, fixtures (sample pane snapshots, sample policy YAML) in `tests/fixtures/`.
- A new public function gets a test in the same session as the function lands. A bug fix gets a regression test that *fails* on `main` and *passes* on the branch.
- Prefer fixture files (`tests/fixtures/snapshots/*.txt`) over inline multi-line strings when the snapshot is realistic-sized.
- `pytest -q` should pass at every commit. CI runs the same matrix on Ubuntu + macOS × Python 3.11/3.12/3.13.

---

## Commands you'll run constantly

```bash
pytest -q                          # ~540 tests, ~4s
pytest tests/unit/test_<name>.py -q
pytest -k <keyword> -q

cldx --version                     # confirm which version is on PATH
cldx                               # interactive picker, attach to a Claude pane
cldx --list-panes                  # show what's in tmux
cldx --auto-detect                 # attach to the only running Claude pane
cldx setup                         # interactive LLM + Telegram setup
cldx setup telegram                # just Telegram
cldx config                        # show current secrets (masked)

./install.sh                       # reinstall after pulling
./install.sh --uninstall           # remove the package, keep ~/.cldx
./uninstall.sh                     # dedicated uninstaller (asks before wiping state)
```

---

## State files you'll touch

| Path | What it is |
|---|---|
| `~/.cldx/config/policy.yml` | Active profile + detection patterns + destructive-op safelist. |
| `~/.cldx/config/agent_name.yml` | Display name for the Telegram bot persona. |
| `~/.cldx/state.yml` | Yolo-learned approval patterns, last-session metadata. |
| `~/.cldx/sessions/<profile>/<ts>.jsonl` | Machine-replayable JSONL event log. |
| `~/.cldx/logs/<date>/<time>_<profile>_<pane>.log` | Plain-text per-session interaction log. |

The defaults that ship with the package are in `cldx/defaults/`. The installer copies them on first run but never overwrites existing user files.

---

## Where features are documented

| File | Audience |
|---|---|
| [`README.md`](./README.md) | New users — install + one-screen overview. |
| [`GUIDELINE.md`](./GUIDELINE.md) | Existing users — full command reference, profile config, troubleshooting. |
| [`FEATURES.md`](./FEATURES.md) | Roadmap — what shipped, what's planned. |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Contributors — workflow, agent rules, local setup. |
| [`SECURITY.md`](./SECURITY.md) | Security researchers — how to report a vulnerability. |
| [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) | Everyone — community expectations. |

Update `FEATURES.md` when a roadmap item ships. Update `README.md` only when user-visible behaviour changes (commands, flags, install steps).

---

## Common gotchas

- **Don't `cd` between `git` invocations** when running multiple git commands — git already operates on the current working tree. Prepending `cd` triggers an unnecessary permission prompt.
- **Don't use `--no-verify`** to skip pre-commit hooks. If a hook fails, fix the underlying cause.
- **`extract_pending_approval` is hardcoded to "Do you want to proceed?"** — it's not pattern-driven yet. If Claude rewords the question, this extractor misses. (Issue worth filing if it becomes a real problem.)
- **The tmux pane width affects how many captured lines a long line becomes.** `tmux capture-pane` reflects the on-screen wrap. Tables and long diffs balloon into many captured lines.
- **`extract_pending_approval` and the classifier's approval-menu pattern are decoupled.** The classifier returns `APPROVAL_MENU` based on `policy.yml` regexes; the extractor pulls out `(question, options)` based on hardcoded structure. They can disagree — fix both if you change either.
- **Don't import `cldx.cli` at module load time elsewhere** — it pulls in Rich, prompt_toolkit, anthropic, telegram-bot. Lazy imports inside functions when you need to reach into `cli` from a smaller module.
