"""Classify the current state of a Claude Code pane snapshot."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cldx.tool_call import ToolCall  # circular-safe under TYPE_CHECKING


class PromptType(str, Enum):
    APPROVAL_YN = "approval_yn"           # "(y/n)" style
    APPROVAL_MENU = "approval_menu"       # "❯ 1. Yes  2. No"
    TEXT_INPUT = "text_input"             # Free-form text expected
    RUNNING = "running"                   # Claude is working
    IDLE = "idle"                         # Nothing happening
    COMPLETE = "complete"                 # Task done


@dataclass
class ClassifiedPrompt:
    type: PromptType
    raw_text: str = ""                    # The matched prompt block
    extracted_command: str | None = None  # e.g. "npm install" or "rm -rf dist"
    context: str = ""                     # Last ~10 lines, for human review
    matched_pattern: str | None = None    # Which pattern fired
    menu_options: tuple[str, ...] = ()    # ("1. Yes", "2. ...", "3. No") for menus
    # Typed view of the tool call this approval is about. Populated when
    # the snapshot contains a recognisable ``⏺ Tool(args)`` line. ``None``
    # for plain Y/N prompts that don't reference a tool (e.g. "Continue?").
    tool: "ToolCall | None" = None

    def signature(self) -> str:
        """Stable fingerprint for deduping repeated detections of the same prompt.

        The signature has to satisfy two competing properties:

        1. **Stable across redraws.** Claude Code repaints its TUI on a
           timer (cursor blink, "Cogitated for Ns" counter); the same
           logical prompt can produce slightly different snapshots from
           frame to frame.
        2. **Distinguishes consecutive prompts.** Claude often asks for
           several approvals in a row with identical menu options
           (``1. Yes / 2. Yes, allow all edits ... / 3. No``) for
           different tool calls (``Write(a.py)``, ``Write(b.md)``).
           Successive prompts MUST hash differently or dispatch dedup
           swallows the later ones and the auto-approval flow stops.

        We assemble the fingerprint from ``(type, extracted_command,
        menu_options)``. ``extracted_command`` is what differs between
        consecutive approvals; menu options keep the signature stable
        under cosmetic redraws. Empty parts are omitted so a Y/N prompt
        without a menu still gets a useful key.
        """
        parts = [self.type.value]
        if self.tool is not None:
            parts.append(f"{self.tool.name}({self.tool.args})")
        elif self.extracted_command:
            parts.append(self.extracted_command)
        if self.menu_options:
            parts.append("|".join(self.menu_options))
        if (
            self.tool is None
            and not self.extracted_command
            and not self.menu_options
        ):
            # Last-ditch fallback: hash the raw text so we still dedup.
            parts.append(self.raw_text)
        return "|".join(parts)


# Generous box-drawing characters Claude Code uses around tool-call panels.
_BOX_CHARS = "│┃┆┇║╎╏▏▕▎▍"
_BOX_PREFIX_RE = re.compile(rf"^\s*[{_BOX_CHARS}]\s?")

# Recognised tool-call lines like `Bash(npm install)`, `Edit(foo.py)`.
_TOOL_CALL_RE = re.compile(
    r"\b(?P<tool>Bash|Read|Edit|Write|Glob|Grep|LS|WebFetch|Run)\b"
    r"\s*\(\s*(?P<arg>[^)]*?)\s*\)"
)

# "Run: <something>" / "Run command: <something>" style lines.
_RUN_HINT_RE = re.compile(
    r"(?:^|\b)(?:Run(?:\s+command)?|Execute|Command)\s*[:\-]\s*(?P<cmd>.+?)\s*$",
    re.MULTILINE,
)

# Menu option lines like "❯ 1. Yes" or "   3. No".
_MENU_OPTION_RE = re.compile(r"^\s*[❯>]?\s*(\d+)\.\s*(.+?)\s*$")

# Anchor word that signals an interactive prompt block. Used to filter out
# unrelated numbered lists that happen to live higher up in the snapshot.
_MENU_ANCHOR_RE = re.compile(r"Do you want|Select an option|❯", re.IGNORECASE)


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled = []
    for raw in patterns or []:
        try:
            compiled.append(re.compile(raw, re.MULTILINE))
        except re.error:
            # Skip malformed user patterns rather than crashing the watcher.
            continue
    return compiled


@dataclass
class _DetectionPatterns:
    approval_yn: list[re.Pattern[str]] = field(default_factory=list)
    approval_menu: list[re.Pattern[str]] = field(default_factory=list)
    text_input: list[re.Pattern[str]] = field(default_factory=list)
    completion: list[re.Pattern[str]] = field(default_factory=list)
    running: list[re.Pattern[str]] = field(default_factory=list)


class PromptClassifier:
    """Classify pane snapshots into a `ClassifiedPrompt`.

    Pattern lists come from `policy.yml -> detection`, so users can adapt
    when Claude Code's UI changes without editing this file.
    """

    # Built-in completion signals — applied IN ADDITION to whatever the
    # user's policy.yml specifies. This protects users whose ``~/.cldx/
    # config/policy.yml`` predates the verb-rotation fix.
    #
    # The structural shape of Claude Code's end-of-turn line is:
    #
    #     ✻ <verb> for <time>
    #
    # where:
    #   - ``<verb>`` rotates randomly across many words, sometimes with
    #     accented letters (Cogitated, Cooked, Baked, Crunched, Churned,
    #     Pondered, Mused, Worked, Sautéed, …). We use ``\S+`` instead
    #     of ``\w+`` so locale-sensitive Unicode word boundaries don't
    #     cost us a match.
    #   - ``<time>`` can be a single unit (``1s``, ``4.5s``, ``3m``) OR
    #     a compound like ``3m 5s`` / ``1h 2m`` / ``1h 30m 5s``. The
    #     repeating group ``(\d+\.?\d*\s*[smhd]\s*)+`` covers all forms.
    _BUILTIN_COMPLETION_PATTERNS: tuple[str, ...] = (
        r"✻\s+\S+\s+for\s+(?:\d+(?:\.\d+)?\s*[smhd]\s*)+",
        r"\? for shortcuts",
    )

    def __init__(
        self,
        detection_cfg: dict | None = None,
        tail_lines: int = 200,
        completion_tail_lines: int = 10,
    ):
        cfg = detection_cfg or {}
        # ``tail_lines`` / ``completion_tail_lines`` are retained for
        # backward compatibility (callers and tests can still override
        # them), but classification no longer slices the snapshot by
        # line count. Instead, it anchors on the LAST ``⏺`` bullet —
        # see :meth:`classify` for the structural algorithm. The line
        # counts are used only as a final-fallback when no ``⏺`` line
        # is present in the snapshot at all (e.g. fresh terminal).
        self.tail_lines = tail_lines
        self.completion_tail_lines = completion_tail_lines
        # Merge user patterns with the built-in fallbacks. Dedup so a user
        # who already listed our generic pattern doesn't compile it twice.
        user_completion = list(cfg.get("completion_patterns", []))
        for builtin in self._BUILTIN_COMPLETION_PATTERNS:
            if builtin not in user_completion:
                user_completion.append(builtin)
        self.patterns = _DetectionPatterns(
            approval_yn=_compile_patterns(cfg.get("approval_yn_patterns", [])),
            approval_menu=_compile_patterns(cfg.get("approval_menu_patterns", [])),
            text_input=_compile_patterns(cfg.get("text_input_patterns", [])),
            completion=_compile_patterns(user_completion),
            running=_compile_patterns(cfg.get("running_patterns", [])),
        )

    # --- Public API ---------------------------------------------------------

    def classify(self, snapshot: str) -> ClassifiedPrompt:
        """Decide the current state of the pane.

        Structural algorithm (how a human reads the pane):

        1. **Find the last ``⏺`` bullet.** Every Claude action/response
           starts with ``⏺``. The most recent ``⏺`` line is where the
           "current answer" begins.
        2. **Take the slice from that ``⏺`` to the end of the snapshot.**
           This is the state region — what Claude is showing right now.
        3. **Inspect that slice for signals:**

           - A question + numbered options (``❯ 1. Yes``…) → ``APPROVAL_MENU``.
           - A ``Y/n`` / ``proceed?`` style line → ``APPROVAL_YN``.
           - A free-form text input prompt → ``TEXT_INPUT``.
           - A ``✻ <verb> for <time>`` line → ``COMPLETE``.
           - An ``esc to interrupt`` / ``Thinking…`` line → ``RUNNING``.
           - Nothing of the above → ``IDLE``.

        This replaces the previous "wide tail vs narrow tail" line-count
        heuristic with a single structural slice — long ``Write(...)`` /
        ``Edit(...)`` previews, multi-paragraph summaries, and TodoWrite
        panels all live *inside* the slice rather than spilling past it.
        Stale ``✻ … for Ns`` lines from earlier turns are *outside* the
        slice (they sit above the last ``⏺``) and cannot false-fire.
        """
        if not snapshot:
            return ClassifiedPrompt(type=PromptType.IDLE)

        lines = snapshot.splitlines()
        last_dot_idx: int | None = None
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].lstrip().startswith("⏺"):
                last_dot_idx = i
                break

        if last_dot_idx is None:
            # No ``⏺`` anywhere in the snapshot — Claude hasn't produced
            # output yet (fresh terminal), the whole turn scrolled off
            # the top, or this is a synthetic/test snapshot with just a
            # prompt. Use the whole snapshot as the scope so any prompt
            # patterns still classify; the structural slice is just the
            # full text.
            scope = snapshot
        else:
            scope = "\n".join(lines[last_dot_idx:])
        context = scope

        # Priority: active prompts > completion > running > idle. Approval
        # must win when both a menu and a ✻ appear in the slice — the
        # menu is the actionable state and must not be swallowed.
        match = self._first_match(self.patterns.approval_menu, scope)
        if match:
            from cldx.tool_call import parse_tool_call as _parse_tool
            return ClassifiedPrompt(
                type=PromptType.APPROVAL_MENU,
                raw_text=match.group(0),
                extracted_command=self._extract_command(scope),
                context=context,
                matched_pattern=match.re.pattern,
                menu_options=self._extract_menu_options(scope),
                tool=_parse_tool(scope),
            )

        match = self._first_match(self.patterns.approval_yn, scope)
        if match:
            from cldx.tool_call import parse_tool_call as _parse_tool
            return ClassifiedPrompt(
                type=PromptType.APPROVAL_YN,
                raw_text=match.group(0),
                extracted_command=self._extract_command(scope),
                context=context,
                matched_pattern=match.re.pattern,
                tool=_parse_tool(scope),
            )

        match = self._first_match(self.patterns.text_input, scope)
        if match:
            return ClassifiedPrompt(
                type=PromptType.TEXT_INPUT,
                raw_text=match.group(0),
                context=context,
                matched_pattern=match.re.pattern,
            )

        match = self._first_match(self.patterns.completion, scope)
        if match:
            return ClassifiedPrompt(
                type=PromptType.COMPLETE,
                raw_text=match.group(0),
                context=context,
                matched_pattern=match.re.pattern,
            )

        match = self._first_match(self.patterns.running, scope)
        if match:
            return ClassifiedPrompt(
                type=PromptType.RUNNING,
                raw_text=match.group(0),
                context=context,
                matched_pattern=match.re.pattern,
            )

        return ClassifiedPrompt(type=PromptType.IDLE, context=context)

    # --- Helpers ------------------------------------------------------------

    @staticmethod
    def _tail(snapshot: str, n: int) -> str:
        lines = snapshot.splitlines()
        return "\n".join(lines[-n:])

    @staticmethod
    def _first_match(patterns: list[re.Pattern[str]], text: str) -> re.Match | None:
        for pat in patterns:
            m = pat.search(text)
            if m:
                return m
        return None

    @staticmethod
    def _extract_command(tail: str) -> str | None:
        """Best-effort: pull out the command/argument Claude is asking about.

        Scans bottom-up so the MOST RECENT ``⏺ Tool(...)`` line wins. With
        a wide tail window, scrollback from prior turns can contain older
        tool calls; we want the one closest to (above) the active approval
        prompt, which is always the latest in pane order. A previous
        version scanned top-down for "stability across redraws", but that
        broke once the tail grew large enough to include other turns.
        """
        lines = tail.splitlines()
        for line in reversed(lines):
            cleaned = _BOX_PREFIX_RE.sub("", line).strip()
            if not cleaned:
                continue
            m = _TOOL_CALL_RE.search(cleaned)
            if m:
                tool = m.group("tool")
                arg = m.group("arg").strip()
                return f"{tool}({arg})" if arg else tool

        # Fallback: "Run: ..." / "Run command: ..." style hint.
        m = _RUN_HINT_RE.search(tail)
        if m:
            return m.group("cmd").strip()

        return None

    @staticmethod
    def _extract_menu_options(tail: str) -> tuple[str, ...]:
        """Pull "1. Yes" / "2. No" style lines that sit near the menu anchor."""
        lines = tail.splitlines()
        # Find the anchor (e.g. "Do you want to proceed?") then collect
        # subsequent numbered lines until the run breaks.
        anchor_idx = None
        for i, line in enumerate(lines):
            if _MENU_ANCHOR_RE.search(line):
                anchor_idx = i
                break
        if anchor_idx is None:
            # No anchor — fall back to any contiguous run of numbered lines.
            start = 0
        else:
            start = anchor_idx

        opts: list[str] = []
        for line in lines[start:]:
            cleaned = _BOX_PREFIX_RE.sub("", line)
            m = _MENU_OPTION_RE.match(cleaned)
            if m:
                opts.append(f"{m.group(1)}. {m.group(2).strip()}")
            elif opts:
                # Stop at the first non-option line after we've started.
                break
        return tuple(opts)
