# Security policy

cldx is a developer-facing tool that drives a coding assistant against your terminal, your filesystem, and optionally your Telegram. We take vulnerability reports seriously.

## Supported versions

| Version  | Supported          |
|----------|--------------------|
| `1.0.x`  | :white_check_mark: |
| `< 1.0`  | :x:                |

Security fixes ship in the latest `1.0.x` release. Older pre-1.0 prototypes are not maintained — upgrade.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.** Public disclosure before a fix is available puts every user at risk.

Instead, report privately via one of:

1. **GitHub Security Advisories** (preferred) — open a draft advisory at  
   <https://github.com/Pranjalab/cldx/security/advisories/new>.  
   This creates a private channel where we can collaborate on a fix.
2. **Email** — send details to the maintainer listed in `pyproject.toml`. If you need encrypted contact, ask in your first message and we'll arrange a key exchange.

Please include:

- A clear description of the issue and the impact (what an attacker can do).
- A minimal reproduction — exact commands, configs, or files involved.
- Affected versions you've confirmed.
- Any suggested mitigations.

## What to expect

| Stage                                      | Target turnaround       |
|--------------------------------------------|-------------------------|
| First acknowledgement of your report       | within **3 business days**   |
| Severity triage + reproduction             | within **7 business days**   |
| Fix released or mitigation documented      | within **30 days** for high/critical issues, best-effort otherwise |
| Public disclosure / advisory               | coordinated with you after the fix ships |

We will credit reporters in the release notes unless you ask to remain anonymous.

## Scope

cldx is a thin orchestration layer around `tmux`, the Claude API, and optionally the Telegram Bot API. Things in scope:

- Bugs that let an external party drive Claude/cldx without authorisation (e.g. forged Telegram replies executing as approvals).
- Path traversal, command injection, or privilege escalation in cldx's own code paths.
- Leakage of secrets stored under `~/.cldx/config/`.
- Bypasses of the destructive-operation safety floor (`rm -rf`, `sudo`, etc.).

Out of scope:

- Vulnerabilities in tmux, Python, Claude Code itself, or the Telegram service — please report those to their respective maintainers. We'll happily coordinate if a cldx-side mitigation exists.
- Issues that require the attacker to already have a local shell as the cldx user.
- Configuration choices a user can make (e.g. running cldx as root).

## Safe-harbour

If you make a good-faith effort to comply with this policy, we will not pursue or support legal action against you for security research. We ask that you:

- Only test against installations you own or are explicitly authorised to test.
- Don't access, exfiltrate, or destroy user data.
- Give us reasonable time to fix issues before public disclosure.

Thanks for helping keep cldx safe.
