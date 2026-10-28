from __future__ import annotations

import os
from pathlib import Path

import pytest

from codewalk.recorder import SUPPORTS_MONITORING

FIXTURES = Path(__file__).parent / "fixtures"
MINIPROJ = FIXTURES / "miniproj"
BACKENDS = ["settrace"] + (["monitoring"] if SUPPORTS_MONITORING else [])


def line_of(path: os.PathLike | str, snippet: str, nth: int = 1) -> int:
    """1-based line number of the nth line containing `snippet`."""
    seen = 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if snippet in line:
                seen += 1
                if seen == nth:
                    return i
    raise AssertionError(f"{snippet!r} not found {nth} time(s) in {path}")


@pytest.fixture(params=BACKENDS)
def backend(request):
    return request.param


@pytest.fixture
def miniproj() -> Path:
    return MINIPROJ
