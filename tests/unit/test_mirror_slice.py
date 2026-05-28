"""Mirror slice computation — anchors on the last ⏺ bullet.

The mirror is the pane Claude shows in cldx. Anchoring on the last ⏺
guarantees the user always sees the full current Claude response —
not just the bottom N lines of whatever's on the pane.
"""

from __future__ import annotations

from cldx.cli import BridgeUI


_slice_start = BridgeUI._compute_mirror_slice_start


def _snapshot_lines(*lines: str) -> list[str]:
    return list(lines)


def test_short_response_uses_tail_minimum():
    """Response shorter than mirror_lines: start at top so the whole
    response is shown (tail covers everything)."""
    lines = _snapshot_lines(
        "⏺ Short answer.",
        "✻ Worked for 1s",
        "❯",
        "  ? for shortcuts",
    )
    # mirror_lines=25, max=200 — snapshot is only 4 lines, so start=0.
    assert _slice_start(lines, 25, 200) == 0


def test_long_response_with_dot_above_tail_anchors_on_dot():
    """The exact regression that prompted this fix.

    Claude's response with a table is ~50 captured lines. The default
    mirror_lines=25 tail would miss the start. Anchoring on the last
    ⏺ shows the full response (the ⏺ line is below the tail start, so
    we move start up to last_dot_idx)."""
    lines = (
        ["⏺ Created three files in test/cldx_classifier_smoke/:"]
        + [f"  table row {n}" for n in range(40)]
        + ["", "✻ Brewed for 1m 10s", "", "─", "❯", "─", "  ? for shortcuts"]
    )
    # n = 1 + 40 + 7 = 48; tail_start (25 lines) = 23; last_dot_idx = 0
    # min(0, 23) = 0 → mirror starts at the ⏺ line.
    assert _slice_start(lines, 25, 200) == 0


def test_dot_inside_tail_keeps_tail_start():
    """When the last ⏺ is within the configured tail, the tail wins —
    we don't truncate further. This preserves backward-compat for
    short responses where the user wants the configured tail size."""
    lines = (
        ["scrollback line %d" % n for n in range(30)]
        + ["⏺ recent answer"]
        + ["body line %d" % n for n in range(5)]
        + ["✻ Worked for 1s", "❯", "  ? for shortcuts"]
    )
    # n = 30 + 1 + 5 + 3 = 39; mirror_lines=25 → tail_start=14;
    # last_dot_idx=30. min(30, 14) = 14 → keep tail_start.
    assert _slice_start(lines, 25, 200) == 14


def test_extremely_long_response_caps_at_max():
    """A 500-line response anchored on a ⏺ near the top must not blow
    out the mirror — cap at mirror_max_lines."""
    lines = (
        ["⏺ huge response"]
        + ["body line %d" % n for n in range(500)]
        + ["✻ Worked for 5m"]
    )
    # n = 502, mirror_max_lines=200 → max_start = 302, last_dot_idx = 0
    # min(0, 477) = 0, but 0 < max_start=302 → bump to 302.
    assert _slice_start(lines, 25, 200) == 502 - 200


def test_no_dot_falls_back_to_tail():
    """A snapshot with no ⏺ at all (fresh terminal, banner-only) should
    just show the configured tail — no anchor to grab onto."""
    lines = (
        ["Welcome to Claude Code"]
        + ["info line %d" % n for n in range(30)]
        + ["❯", "  ? for shortcuts"]
    )
    # n=33; tail_start = max(0, 33-25) = 8; no ⏺ → return tail_start.
    assert _slice_start(lines, 25, 200) == 8


def test_empty_snapshot_returns_zero():
    assert _slice_start([], 25, 200) == 0
