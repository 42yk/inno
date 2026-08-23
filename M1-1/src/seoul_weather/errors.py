"""패키지 전체에서 공유하는 명시적 오류."""


class DataDownloadError(RuntimeError):
    """데이터 발견, 다운로드 또는 압축 파일 검증 실패."""


class DataValidationError(RuntimeError):
    """원본 또는 가공 데이터 계약 위반."""


class AnalysisValidationError(RuntimeError):
    """분석 입력 데이터가 필수 계약을 위반함."""
