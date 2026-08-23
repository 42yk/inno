"""헤드리스 환경에서도 재현 가능한 Matplotlib 설정."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "seoul-temperature-analysis-cache"
_MATPLOTLIB_CACHE = _RUNTIME_CACHE_ROOT / "matplotlib"
_XDG_CACHE = _RUNTIME_CACHE_ROOT / "xdg"
_MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
_XDG_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MATPLOTLIB_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(_XDG_CACHE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager


# 그래프 스타일과 한글 글꼴을 설정하고 사용 여부를 반환한다.
def configure_plot_style() -> bool:
    """사용 가능한 한글 글꼴을 설정하고 사용 여부를 반환한다."""

    plt.style.use("seaborn-v0_8-whitegrid")
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in (
        "AppleGothic",
        "Malgun Gothic",
        "NanumGothic",
        "Noto Sans CJK KR",
    ):
        if candidate in available_fonts:
            plt.rcParams["font.family"] = candidate
            plt.rcParams["axes.unicode_minus"] = False
            return True
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = True
    return False
