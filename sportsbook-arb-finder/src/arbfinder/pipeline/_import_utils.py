"""Internal helpers shared across the pipeline package."""

from __future__ import annotations

import importlib

__all__ = ["import_class"]


def import_class(dotted_path: str):
    """Dynamically import a class from a dotted module path.

    e.g. ``import_class("arbfinder.parsers.draftkings.DraftKingsParser")``
    returns the ``DraftKingsParser`` class itself (not an instance).
    """
    module_path, _, class_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)