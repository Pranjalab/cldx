# Summary

<!-- One or two sentences on what this PR changes and why. Link the issue it closes if relevant: `Fixes #123`. -->

## Testing checklist

- [ ] `pytest -q` passes locally
- [ ] Added/updated unit tests covering the new behaviour
- [ ] Manual run of `cldx` against a real tmux pane (where applicable)
- [ ] Telegram bridge smoke-checked (if this PR touches `cldx/telegram_*`)
- [ ] Policy / wait-bar behaviour verified end-to-end (if this PR touches the approval flow)

## Verification steps

<!-- Paste the exact commands a reviewer can run to confirm the change works.

Example:
```
./install.sh
cldx --auto-detect
# expected: …
```
-->

## Dependency impact

- [ ] No new runtime dependencies
- [ ] New dependency added (note in `pyproject.toml`, justify below)
- [ ] Dev-only dependency added

<!-- If you added or upgraded anything, explain the why here. -->

## Screenshots / logs

<!-- Optional. Drop terminal screenshots or `~/.cldx/logs/` snippets that show the before/after. -->

## Checklist

- [ ] I read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`
- [ ] My changes follow the existing code style and naming conventions
- [ ] I updated `README.md` / `GUIDELINE.md` / `FEATURES.md` if user-facing behaviour changed
