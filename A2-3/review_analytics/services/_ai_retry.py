"""인공지능 Service 실행을 위한 작은 동기 재시도 도우미를 제공한다."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from review_analytics.errors import AIServiceError


T = TypeVar("T")


# AI 작업을 지수 백오프로 제한 횟수만큼 재시도한다.
def retry_ai(
    operation: Callable[[], T],
    retry_count: int,
    sleep: Callable[[float], object],
    on_retry: Callable[[int, AIServiceError], object] | None = None,
) -> T:
    for attempt in range(retry_count + 1):
        try:
            return operation()
        except AIServiceError as exc:
            if attempt == retry_count:
                raise
            if on_retry is not None:
                on_retry(attempt + 1, exc)
            sleep(float(2**attempt))
    raise AssertionError("unreachable")
