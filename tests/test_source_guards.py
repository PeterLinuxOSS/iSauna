"""Source-level guards for bugs that only show up inside a running HA.

The pure protocol tests cannot catch these: the offending code lives in
coordinator.py, which imports Home Assistant, so it is never executed here.
Parsing the source is the cheapest guard that still fails loudly in CI.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "custom_components" / "isauna"

# Home Assistant helpers that are sync @callback despite the async_ prefix.
# Awaiting one raises "TypeError: 'NoneType' object can't be awaited" at the
# worst possible moment -- inside async_unload_entry, which then leaves the
# config entry half-torn-down and every entity unavailable until a restart.
# Cost of learning this the hard way: 2026-09-12, sauna dead for an evening.
SYNC_CALLBACKS = {
    "async_shutdown": "Debouncer.async_shutdown",
    "async_cancel": "Debouncer.async_cancel",
}


def _awaited_attribute_calls(tree: ast.AST):
    """Yield (attr, receiver) for every `await <receiver>.<attr>()` in the tree."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Await):
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue
        receiver = call.func.value
        name = receiver.attr if isinstance(receiver, ast.Attribute) else ""
        yield call.func.attr, name


def test_no_sync_home_assistant_callback_is_awaited():
    """`await debouncer.async_shutdown()` is a TypeError, not a no-op."""
    for path in sorted(_SRC.glob("*.py")):
        tree = ast.parse(path.read_text())
        for attr, receiver in _awaited_attribute_calls(tree):
            if attr in SYNC_CALLBACKS and "debouncer" in receiver.lower():
                raise AssertionError(
                    f"{path.name}: awaits {SYNC_CALLBACKS[attr]}, which is a sync "
                    f"@callback returning None -- drop the await"
                )


def test_the_guard_would_notice_the_original_bug():
    """Without this, a green run proves nothing about the check itself."""
    tree = ast.parse(
        "async def f(self):\n    await self._apply_debouncer.async_shutdown()\n"
    )
    found = [
        attr
        for attr, receiver in _awaited_attribute_calls(tree)
        if attr in SYNC_CALLBACKS and "debouncer" in receiver.lower()
    ]
    assert found == ["async_shutdown"]
