from __future__ import annotations

import ast
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "seoul_weather"
HANGUL_PATTERN = re.compile(r"[가-힣]")


def test_every_source_function_has_korean_role_comment() -> None:
    missing_comments: list[str] = []
    comments_by_function: dict[tuple[str, str], str] = {}

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        for function in functions:
            first_line = min(
                [decorator.lineno for decorator in function.decorator_list]
                or [function.lineno]
            )
            previous_index = first_line - 2
            while previous_index >= 0 and not lines[previous_index].strip():
                previous_index -= 1
            previous_line = (
                lines[previous_index].strip() if previous_index >= 0 else ""
            )
            if not previous_line.startswith("#") or not HANGUL_PATTERN.search(
                previous_line
            ):
                relative_path = path.relative_to(PROJECT_ROOT)
                missing_comments.append(
                    f"{relative_path}:{function.lineno} {function.name}"
                )
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            comments_by_function[(relative_path, function.name)] = previous_line

    assert not missing_comments, "한글 역할 주석 누락:\n" + "\n".join(
        missing_comments
    )

    reviewed_comments = {
        (
            "src/seoul_weather/analytics/statistics.py",
            "compute_monthly_statistics",
        ): "# 관측률 기준을 적용해 연도별 월평균과 월 장기평균 대비 편차를 계산한다.",
        (
            "src/seoul_weather/processing/dataset.py",
            "combine_year_frames",
        ): "# 연도별 데이터를 합치고 동일 중복은 제거·기록하며 충돌 중복은 거부한다.",
        (
            "src/seoul_weather/visualization/style.py",
            "configure_plot_style",
        ): "# 그래프 스타일과 한글 글꼴을 설정하고 사용 여부를 반환한다.",
        (
            "src/seoul_weather/workflows/download.py",
            "run_download",
        ): "# 표준 CSV 준비 흐름을 호출하고 파일 작업 오류를 도메인 오류로 변환한다.",
    }
    for key, expected_comment in reviewed_comments.items():
        assert comments_by_function[key] == expected_comment
