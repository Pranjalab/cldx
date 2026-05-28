# Contributing to cldx

Thanks for considering a contribution. cldx is a small, opinionated tool and we keep the contribution loop tight on purpose — read this page once, you should be unblocked from there.

If you haven't yet, please skim [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) and [`FEATURES.md`](./FEATURES.md) before you start. The first tells you how we work together; the second tells you which ideas already have a home.

---

## Local development setup

cldx targets Python **3.11+**. Anything in 3.11 / 3.12 / 3.13 should work — CI runs all three on Linux and macOS.

```bash
git clone https://github.com/Pranjalab/cldx.git
cd cldx

python3.13 -m venv .venv          # or 3.12 / 3.11
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev,all-llm]"
```

`-e` (editable) installs cldx so the `cldx` script in your venv reflects your live source — no re-install after each change.

You'll also want **tmux** on your PATH:

- macOS: `brew install tmux`
- Ubuntu/Debian: `sudo apt-get install tmux`

---

## Running the tests

```bash
pytest -q                          # the whole suite (fast)
pytest tests/unit/test_session_picker.py -q
pytest -k startup -q               # by keyword
pytest --maxfail=1 -x              # stop on first failure
```

All tests live under [`tests/`](./tests). Unit tests go in `tests/unit/`; integration tests go in `tests/integration/`. New behaviour needs a unit test — if your PR adds code paths but no tests, expect a request for them.

---

## Formatting & linting

We don't enforce a heavyweight formatter, but please match the surrounding style:

- 4-space indents, double-quote strings, type hints where they help.
- One module-level docstring per file. Use docstrings on public functions; keep them tight.
- No `from __future__ import annotations` clean-up commits — leave the existing layout alone unless your PR genuinely needs the change.
- Don't add `print()` debug noise. Use `console.print(...)` from Rich or the existing `interaction_log` helpers.

If you have `ruff` installed, `ruff check cldx` is a good lightweight sanity pass.

---

## Pull request workflow

1. **Open an issue first** for non-trivial changes — features, refactors, anything that changes user-facing behaviour. A short discussion saves a lot of "please rework this" later.
2. **Branch from `main`.** Name the branch after the change (`fix/tmux-no-server`, `feat/policy-glob-rules`).
3. **Make small, reviewable commits.** Squash on merge is fine but well-titled commits help reviewers.
4. **Run `pytest -q` locally** before pushing. CI runs the same matrix, but red CI on a freshly-opened PR slows everything down.
5. **Fill out the PR template.** Especially the "verification steps" — they're how the reviewer reproduces your change.
6. **Expect review feedback.** We optimise for clarity over cleverness; if a reviewer asks for a simpler approach, that's the rule.

If you're unsure whether a change belongs in cldx, open a *Feature request* issue first and describe the use case. The fastest path to a "yes" is showing the concrete itch the feature scratches.

---

## Releasing

(Maintainers only.) Tagging a GitHub release triggers `.github/workflows/publish.yml`, which builds and pushes to PyPI via OIDC trusted publishing. There's no manual `twine upload` step.

---

## Questions?

Open a discussion or a low-stakes issue — we'd rather answer the same question ten times than have someone bounce off a confusing setup.
