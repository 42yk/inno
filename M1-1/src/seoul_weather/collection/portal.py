"""기상자료개방포털 파일셋 조회와 다운로드 요청 구성."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from seoul_weather.errors import DataDownloadError


LISTING_URL = "https://data.kma.go.kr/data/grnd/selectAsosList.do?pgmNo=34"
DOWNLOAD_URL = "https://data.kma.go.kr/data/common/processDtsSampleReqst.do"
REQUEST_TIMEOUT = (10, 60)


@dataclass(frozen=True)
class FileSetInfo:
    """기상자료개방포털 파일셋 식별 정보."""

    size_kb: float
    fileset_id: str
    relative_path: str
    detail_id: str
    filename: str


# 대상 연도와 지점의 파일셋 조회 요청 값을 구성한다.
def build_listing_payload(year: int, station_id: int = 108) -> dict[str, str]:
    return {
        "lrgClssCd": "SFC",
        "mddlClssCd": "SFC01",
        "serviceSe": "F00101",
        "menuNo": "32",
        "pgmNo": "34",
        "dataFormCd": "F00501",
        "startDt": str(year),
        "endDt": str(year),
        "stnIds": str(station_id),
        "pageIndex": "1",
    }


# 조회 HTML에서 조건에 맞는 단일 파일셋 식별 정보를 추출한다.
def parse_fileset_info(html: str, year: int, station_id: int = 108) -> FileSetInfo:
    soup = BeautifulSoup(html, "html.parser")
    filename_prefix = f"SURFACE_ASOS_{station_id}_DAY_{year}_{year}_"
    matches: list[FileSetInfo] = []

    for input_element in soup.select('input[name="fileSizeMgList"]'):
        raw_value = input_element.get("value")
        if not isinstance(raw_value, str):
            continue
        fields = raw_value.split("^")
        if len(fields) != 4:
            continue
        size_text, fileset_id, relative_path, detail_id = fields
        filename = PurePosixPath(relative_path).name
        if filename.startswith(filename_prefix) and filename.endswith(".zip"):
            try:
                size_kb = float(size_text)
            except ValueError as exc:
                raise DataDownloadError(
                    f"{year}년 파일 크기 정보를 숫자로 해석할 수 없습니다: "
                    f"{size_text!r}"
                ) from exc
            matches.append(
                FileSetInfo(
                    size_kb=size_kb,
                    fileset_id=fileset_id,
                    relative_path=relative_path,
                    detail_id=detail_id,
                    filename=filename,
                )
            )

    if not matches:
        raise DataDownloadError(
            f"서울 지점 {station_id}의 {year}년 ASOS 일자료 파일을 찾지 못했습니다."
        )
    if len(matches) > 1:
        raise DataDownloadError(
            f"서울 지점 {station_id}의 {year}년 ASOS 일자료 파일을 여러 개 찾았습니다."
        )
    return matches[0]


# 조회 결과를 이용해 파일 다운로드 요청 값을 구성한다.
def build_download_payload(
    info: FileSetInfo, year: int, station_id: int = 108
) -> dict[str, str]:
    payload = build_listing_payload(year=year, station_id=station_id)
    payload.update(
        {
            "fileSizeMgList": (
                f"{info.size_kb:g}^{info.fileset_id}^{info.relative_path}^"
                f"{info.detail_id}"
            ),
            "filesetSnList": info.fileset_id,
            "filesetDtlSnList": info.detail_id,
        }
    )
    return payload


# 일시적 HTTP 오류를 재시도하는 수집용 세션을 생성한다.
def create_http_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "seoul-temperature-analysis/1.0 (public-data research)"}
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
