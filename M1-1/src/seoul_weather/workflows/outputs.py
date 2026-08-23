"""여러 workflow 산출물을 함께 승격하고 실패 시 원상 복구한다."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path


# 여러 staging 파일을 함께 승격하고 실패하면 기존 파일을 복구한다.
def promote_files_with_rollback(
    pairs: Sequence[tuple[Path, Path]],
    *,
    error_type: type[RuntimeError],
    error_message: str,
) -> None:
    """staging 파일들을 승격하고 중간 실패 시 기존 파일을 복구한다."""

    promotions = [(Path(source), Path(destination)) for source, destination in pairs]
    if not promotions:
        return

    sources = [source for source, _ in promotions]
    destinations = [destination for _, destination in promotions]
    if len(set(sources)) != len(sources):
        raise error_type(f"{error_message} staging 경로가 중복되었습니다.")
    if len(set(destinations)) != len(destinations):
        raise error_type(f"{error_message} 최종 경로가 중복되었습니다.")

    try:
        for source, destination in promotions:
            if source == destination:
                raise error_type(
                    f"{error_message} staging 경로와 최종 경로가 같습니다: {source}"
                )
            if not source.is_file():
                raise error_type(
                    f"{error_message} staging 파일이 없습니다: {source}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and not destination.is_file():
                raise error_type(
                    f"{error_message} 최종 경로가 파일이 아닙니다: {destination}"
                )
    except OSError as exc:
        raise error_type(error_message) from exc

    token = uuid.uuid4().hex
    backups: list[tuple[Path, Path]] = []
    promoted_destinations: list[Path] = []
    try:
        for destination in destinations:
            if destination.exists():
                backup = destination.with_name(
                    f".{destination.name}.{token}.backup"
                )
                destination.replace(backup)
                backups.append((backup, destination))

        for source, destination in promotions:
            source.replace(destination)
            promoted_destinations.append(destination)
    except OSError as exc:
        rollback_errors = _rollback_promotions(
            promoted_destinations=promoted_destinations,
            backups=backups,
        )
        detail = (
            f" 복구 중 오류 {len(rollback_errors)}건이 추가로 발생했습니다."
            if rollback_errors
            else ""
        )
        raise error_type(f"{error_message}{detail}") from exc

    for backup, _ in backups:
        try:
            backup.unlink(missing_ok=True)
        except OSError:
            pass


# 승격된 파일을 제거하고 backup을 되돌리며 복구 오류를 수집한다.
def _rollback_promotions(
    *,
    promoted_destinations: Sequence[Path],
    backups: Sequence[tuple[Path, Path]],
) -> list[OSError]:
    errors: list[OSError] = []
    for destination in reversed(promoted_destinations):
        try:
            destination.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(exc)
    for backup, destination in reversed(backups):
        try:
            if backup.exists():
                backup.replace(destination)
        except OSError as exc:
            errors.append(exc)
    return errors
