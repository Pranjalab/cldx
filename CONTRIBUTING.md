# Contributing to cldx

Thanks for considering a contribution. cldx is a small, opinionated tool and we keep the contribution loop tight on purpose — read this page once, you should be unblocked from there.

If you haven't yet, please skim [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) and [`FEATURES.md`](./FEATURES.md) before you start. The first tells you how we work together; the second tells you which ideas already have a home.

---

## Where to start: open issues

We track everything in the [GitHub issues list](https://github.com/Pranjalab/cldx/issues). That's the single source of truth for "what needs doing" — pick from there rather than guessing.

| Label | What it means |
|---|---|
| `good first issue` | Small, well-scoped, low-context-needed. Best entry point. |
| `bug` | Something is broken. Fix + regression test. |
| `enhancement` | New feature or improvement. Discuss in the issue before coding. |
| `help wanted` | The maintainers welcome external contributions on this one. |
| `needs-investigation` | The cause isn't clear yet. Comment with findings before submitting code. |

If you don't see anything that fits, **open a new issue first** — see [`bug_report.md`](./.github/ISSUE_TEMPLATE/bug_report.md) and [`feature_request.md`](./.github/ISSUE_TEMPLATE/feature_request.md) templates. Don't open a PR for non-trivial work without a matching issue; reviewers want to discuss the *what* before they review the *how*.

---

## Issue → PR workflow

The contribution loop has six steps. Skipping any of them slows the PR down.

### 1. Find or open an issue

Either pick an open issue or open a new one with the appropriate template.

### 2. Claim it

Drop a comment on the issue saying you're picking it up — e.g. *"I'll take this; aiming to open a PR by end of week."* This avoids two people doing the same work, and lets a maintainer flag any pitfalls *before* you start. If the issue has been silent for a few days and you haven't heard back, just go ahead — claiming is courtesy, not a lock.

### 3. Set up locally

```bash
git clone https://github.com/Pranjalab/cldx.git
cd cldx

python3.13 -m venv .venv          # or 3.12 / 3.11
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev,all-llm]"
```

`-e` (editable) installs cldx so the `cldx` script in your venv reflects your live source — no re-install after each change. You'll also want **tmux** on PATH (`brew install tmux` / `apt-get install tmux`).

### 4. Branch + develop

```bash
git checkout -b fix/<short-slug>      # e.g. fix/session-limit-reset-alert
# or
git checkout -b feat/<short-slug>     # e.g. feat/policy-glob-rules
```

Branch names: `fix/...`, `feat/...`, `docs/...`, `refactor/...`, `test/...`.

While developing:

- Match the surrounding code style. Type hints where they help. Module-level docstring per file.
- One responsibility per PR. If you find a separate bug while fixing the original, file a separate issue and PR.
- New code paths need new tests. Bug fixes need a regression test that *fails* on `main` and *passes* on your branch.
- Don't add dependencies without saying why in the PR description.
- Run `pytest -q` locally before pushing. CI runs the same matrix on Linux + macOS × Python 3.11/3.12/3.13.

### 5. Open the PR

Push your branch and open a PR against `main`. The [PR template](./.github/PULL_REQUEST_TEMPLATE.md) walks you through everything you need to include — please don't skip the *verification steps* section, that's how the reviewer reproduces your change.

Critical: link the issue. The PR body should contain `Fixes #123` (or `Closes #123` / `Refs #123`) so GitHub auto-closes the issue when the PR merges.

A good PR title is short and starts with a verb: *"fix tmux startup crash when no server is running"*, *"add Bedrock LLM backend"*. Skip the prefix tags — the labels do that.

### 6. Address review

Expect at least one round of review. We optimise for clarity over cleverness; if a reviewer asks for a simpler approach, that's the rule. Push fixup commits to your branch (don't force-push during review — it makes inline comments hard to follow). When the reviewer approves, they'll squash-merge.

---

## Contributing as an LLM agent

cldx accepts contributions from autonomous coding agents (Claude Code, Codex, Cursor, Aider, etc) under the same standards as human contributors — *but with sharper rules*, because agents fabricate plausible-looking work more easily than humans do.

If you're an agent reading this, **follow every rule below**. If a human is supervising you, they're responsible for enforcing these; treat them as non-negotiable.

### Hard requirements

1. **Pick a real open issue.** Don't invent one. Drop a claim comment on the issue before you start. If no fitting issue exists, surface that to your supervisor — don't open speculative PRs.
2. **Run the test suite.** Every commit must pass `pytest -q` locally. If tests fail, fix the cause; never delete or skip a failing test to make the PR green.
3. **Write regression tests for bugs.** A bug-fix PR without a test that fails on `main` and passes on your branch will be rejected.
4. **No fabricated context in commit messages or PR descriptions.** If you didn't verify something, don't claim you did. "Tested manually" must mean a human ran the change.
5. **Cite file paths and line numbers** when describing what you changed. Use `path/to/file.py:42` style so reviewers can navigate.
6. **No dependency additions without a paragraph explaining why** in the PR description. Prefer stdlib + already-pulled-in libraries.
7. **Don't reformat unrelated code.** Style-only changes outside the PR's scope make review harder. Match the surrounding style of files you touch and stop there.
8. **Don't bump versions, edit `CHANGELOG`s, or modify CI workflows** unless the issue explicitly asks for it.
9. **Don't merge your own PRs.** Wait for human review.
10. **If you get stuck, say so.** A PR description that says "I couldn't get test X to pass; here's what I tried" is welcome. Hallucinated "done" claims waste reviewer time.

### Recommended workflow for agents

1. Read the issue end-to-end. Re-read the comments — context drift between issue body and discussion is common.
2. Read [`CLAUDE.md`](./CLAUDE.md) (project context), [`GUIDELINE.md`](./GUIDELINE.md) (command reference), and the most relevant module in `cldx/`. Don't skim — agents lose accuracy fast when the context they read doesn't match what they edit.
3. State your plan in 3-5 sentences in the PR description. Reviewers should be able to predict the diff from the plan.
4. Make the change. Run tests after every meaningful edit, not just at the end.
5. Fill in the PR template *honestly* — every checkbox should reflect work you actually did.

### What agents should NOT do

- Rewrite the README "while you're in there."
- Add `# noqa`, `# type: ignore`, `# pragma: no cover` comments to silence linters/checkers — fix the underlying issue.
- Bypass pre-commit hooks (`--no-verify`).
- Push to `main` directly.
- Open a flurry of micro-PRs to game contribution stats.

The reviewer's signal that an agent contribution went well: the PR is small, scoped, linked to an issue, tests pass, and the description accurately describes what changed. That's the bar.

---

## Local development reference

```bash
pytest -q                          # full suite (currently ~540 tests, runs in ~4s)
pytest tests/unit/test_<name>.py -q
pytest -k <keyword> -q             # filter by test name
pytest --maxfail=1 -x              # stop on first failure
```

All tests live under [`tests/`](./tests). Unit tests in `tests/unit/`, integration tests in `tests/integration/`. Fixtures in `tests/fixtures/`.

Static checks (optional but encouraged):

```bash
ruff check cldx                    # if you have ruff installed
```

We don't enforce a heavyweight formatter — match surrounding style. 4-space indents, double-quote strings, type hints where they help.

---

## Releases

(Maintainers only.) Tagging a GitHub release triggers [`.github/workflows/publish.yml`](./.github/workflows/publish.yml), which builds and pushes to PyPI via OIDC trusted publishing. No manual `twine upload` step.

---

## Questions?

Open a discussion or a low-stakes issue — we'd rather answer the same question ten times than have someone bounce off a confusing setup. And do read [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) — it's the contract we hold all contributors (human and agent) to.
