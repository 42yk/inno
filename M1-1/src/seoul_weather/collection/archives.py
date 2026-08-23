"""ZIP 응답 검증과 중첩 압축 원본 보존."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from seoul_weather.errors import DataDownloadError


# 응답 바이트가 정상 ZIP이며 내부 파일도 손상되지 않았는지 검사한다.
def validate_zip_bytes(content: bytes, label: str) -> None:
    if not content.startswith(b"PK"):
        raise DataDownloadError(f"{label} 응답이 ZIP 형식이 아닙니다.")
    try:
        with ZipFile(BytesIO(content)) as archive:
            bad_member = archive.testzip()
    except BadZipFile as exc:
        raise DataDownloadError(f"{label} ZIP 파일이 손상되었습니다.") from exc
    if bad_member is not None:
        raise DataDownloadError(
            f"{label} ZIP 내부 파일이 손상되었습니다: {bad_member}"
        )


# 기존 원본을 보호하면서 새 파일을 임시 경로를 거쳐 저장한다.
def write_preserving_existing(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() == content:
            return
        raise DataDownloadError(
            f"기존 원본 파일의 내용이 달라 덮어쓰지 않습니다: {path}"
        )
    temporary_path = path.with_name(f".{path.name}.part")
    temporary_path.write_bytes(content)
    temporary_path.replace(path)


# 바깥 ZIP에서 지정한 안쪽 ZIP과 단일 CSV를 찾아 원본 그대로 보존한다.
def extract_nested_archives(
    outer_zip_path: Path,
    year_dir: Path,
    expected_inner_filename: str,
) -> tuple[Path, Path]:
    outer_bytes = outer_zip_path.read_bytes()
    validate_zip_bytes(outer_bytes, f"{outer_zip_path.name} 바깥 압축 파일")

    with ZipFile(BytesIO(outer_bytes)) as outer_archive:
        matching_inner_names = [
            name
            for name in outer_archive.namelist()
            if PurePosixPath(name).name == expected_inner_filename
        ]
        if len(matching_inner_names) != 1:
            raise DataDownloadError(
                f"예상한 안쪽 ZIP {expected_inner_filename!r}을 정확히 한 개 "
                f"찾아야 하지만 {len(matching_inner_names)}개입니다."
            )
        inner_bytes = outer_archive.read(matching_inner_names[0])

    validate_zip_bytes(inner_bytes, expected_inner_filename)
    with ZipFile(BytesIO(inner_bytes)) as inner_archive:
        csv_names = [
            name
            for name in inner_archive.namelist()
            if not name.endswith("/")
            and PurePosixPath(name).suffix.lower() == ".csv"
        ]
        if len(csv_names) != 1:
            raise DataDownloadError(
                f"{expected_inner_filename} 안에서 CSV를 정확히 한 개 찾아야 하지만 "
                f"{len(csv_names)}개입니다."
            )
        csv_name = PurePosixPath(csv_names[0]).name
        csv_bytes = inner_archive.read(csv_names[0])

    year_dir.mkdir(parents=True, exist_ok=True)
    inner_path = year_dir / expected_inner_filename
    csv_path = year_dir / csv_name
    write_preserving_existing(inner_path, inner_bytes)
    write_preserving_existing(csv_path, csv_bytes)
    return inner_path, csv_path
