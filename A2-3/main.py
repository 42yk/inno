"""리뷰 감정 분석 CLI의 실행 진입점이다."""

from __future__ import annotations

from review_analytics.cli import run


# CLI를 실행하고 프로세스 종료 코드를 반환한다.
def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
