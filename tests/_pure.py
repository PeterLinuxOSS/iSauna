"""Load the Home Assistant-free modules without running the package __init__.

``custom_components/isauna/__init__.py`` imports Home Assistant, which these
unit tests deliberately do not depend on -- so importing the package normally
would drag the whole of HA into the test run. ``protocol.py`` and ``const.py``
are written to be free of HA imports, and this loader is what lets that promise
pay off: it registers a synthetic package so their relative imports resolve.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_PKG = "isauna_pure"
_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "isauna"


def _load() -> dict:
    package = types.ModuleType(_PKG)
    package.__path__ = [str(_DIR)]
    sys.modules[_PKG] = package

    loaded = {}
    for name in ("const", "protocol"):
        spec = importlib.util.spec_from_file_location(
            f"{_PKG}.{name}", _DIR / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{_PKG}.{name}"] = module
        spec.loader.exec_module(module)
        loaded[name] = module
    return loaded


_MODULES = _load()
const = _MODULES["const"]
protocol = _MODULES["protocol"]
