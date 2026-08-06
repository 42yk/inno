"""텍스트와 선택 리뷰 날짜를 순수 함수로 정규화한다."""

import re
import unicodedata
from datetime import date, datetime


_WHITESPACE = re.compile(r"\s+")
_DATE_FORMATS = ("%Y/%m/%d", "%Y.%m.%d")


# 임의 값을 NFKC 텍스트로 바꾸고 공백을 한 칸으로 정리한다.
def normalize_text(value: object) -> str:
    """Return NFKC-normalized text with leading/trailing and repeated space removed."""
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value)).strip()
    return _WHITESPACE.sub(" ", normalized)


# 지원하는 날짜 표현을 ISO 날짜로 정규화한다.
def normalize_date(value: object) -> str | None:
    """Return a parseable date as ISO text, or ``None`` when it is absent/invalid."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = normalize_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        try:
            return datetime.fromisoformat(text).date().isoformat()
        except ValueError:
            pass
        for date_format in _DATE_FORMATS:
            try:
                return datetime.strptime(text, date_format).date().isoformat()
            except ValueError:
                continue
    return None


# 중복 비교용 텍스트를 대소문자와 공백 차이 없이 정규화한다.
def normalize_fingerprint_text(value: object) -> str:
    """Normalize text for duplicate identity, including case-insensitive comparison."""
    return normalize_text(value).casefold()


# 중복 비교용 날짜를 ISO 값 또는 정규화 원문으로 만든다.
def normalize_fingerprint_date(value: object) -> str:
    """Use ISO form when possible, otherwise the normalized original text."""
    return normalize_date(value) or normalize_fingerprint_text(value)
