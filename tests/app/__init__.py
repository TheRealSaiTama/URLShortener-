"""Shim package to expose the project package when tests run as scripts."""

from __future__ import annotations

from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "app"
__path__ = [str(_PACKAGE_ROOT)]
__file__ = str(_PACKAGE_ROOT / "__init__.py")
if __spec__ is not None:
    __spec__.submodule_search_locations = __path__
