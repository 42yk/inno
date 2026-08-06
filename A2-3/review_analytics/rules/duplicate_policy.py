"""원본 형식과 별점에 영향받지 않는 안정적인 중복 지문을 만든다."""

import hashlib
import json

from review_analytics.rules.normalization import normalize_fingerprint_date, normalize_fingerprint_text


# 본문·제품·날짜의 정규화 값으로 안정적인 중복 지문을 만든다.
def fingerprint_review(text: object, product: object, review_date: object) -> str:
    """Return the documented SHA-256 fingerprint for a raw review identity."""
    payload = [
        normalize_fingerprint_text(text),
        normalize_fingerprint_text(product),
        normalize_fingerprint_date(review_date),
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
