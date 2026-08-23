from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from seoul_weather import cli
from seoul_weather.errors import DataValidationError


@pytest.mark.parametrize("command", ["download", "analyze", "run"])
def test_cli_has_required_subcommands(command: str) -> None:
    parser = cli.build_parser()

    args = parser.parse_args([command])

    assert args.command == command


def test_cli_run_accepts_offline_rebuild_and_project_paths(tmp_path: Path) -> None:
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "--project-root",
            str(tmp_path),
            "run",
            "--rebuild-from-raw",
            "--processed",
            "custom.csv",
        ]
    )

    assert args.project_root == tmp_path
    assert args.rebuild_from_raw is True
    assert args.processed == Path("custom.csv")


def test_cli_run_rejects_analysis_scope_override() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--start-year", "2000"])


def test_cli_returns_one_and_prints_domain_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli, "run_download", lambda **kwargs: (_ for _ in ()).throw(
            DataValidationError("원자료가 없습니다")
        )
    )

    exit_code = cli.main(["download"])

    assert exit_code == 1
    assert "오류: 원자료가 없습니다" in capsys.readouterr().err


@pytest.mark.parametrize("command", [None, "download", "analyze", "run"])
def test_package_entrypoint_exposes_help(command: str | None) -> None:
    arguments = [sys.executable, "-m", "seoul_weather"]
    if command is not None:
        arguments.append(command)
    arguments.append("--help")

    result = subprocess.run(arguments, check=True, capture_output=True, text=True)

    assert "usage: seoul-weather" in result.stdout


def test_package_and_console_entrypoints_have_same_help() -> None:
    console_path = Path(sys.executable).with_name("seoul-weather")
    assert console_path.is_file(), "editable 설치로 콘솔 명령이 생성되어야 합니다"

    package = subprocess.run(
        [sys.executable, "-m", "seoul_weather", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    console = subprocess.run(
        [str(console_path), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert console.stdout == package.stdout


def test_package_run_rebuilds_and_analyzes_offline(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    processed_path = tmp_path / "processed.csv"
    summary_path = tmp_path / "summary.json"
    image_dir = tmp_path / "images"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "seoul_weather",
            "--project-root",
            str(project_root),
            "run",
            "--rebuild-from-raw",
            "--processed",
            str(processed_path),
            "--output-dir",
            str(image_dir),
            "--summary",
            str(summary_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "11,323행" in result.stdout
    assert processed_path.is_file()
    assert summary_path.is_file()
    assert len(list(image_dir.glob("*.png"))) == 3


def test_package_analyze_reports_invalid_csv_without_traceback(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "invalid.csv"
    invalid_path.write_bytes(b"\xff\xfe\x00")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "seoul_weather",
            "analyze",
            "--input",
            str(invalid_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "오류:" in result.stderr
    assert "Traceback" not in result.stderr


def test_package_analyze_reports_output_path_error_without_traceback(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    output_file = tmp_path / "images"
    output_file.write_text("not a directory", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "seoul_weather",
            "--project-root",
            str(project_root),
            "analyze",
            "--output-dir",
            str(output_file),
            "--summary",
            str(tmp_path / "summary.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "오류:" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["download", "--rebuild-from-raw", "--output", "/"],
        ["run", "--rebuild-from-raw", "--processed", "/"],
    ],
)
def test_package_commands_report_nameless_output_path_without_traceback(
    arguments: list[str],
) -> None:
    project_root = Path(__file__).parents[1]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "seoul_weather",
            "--project-root",
            str(project_root),
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "오류:" in result.stderr
    assert "출력 경로" in result.stderr
    assert "Traceback" not in result.stderr


def test_previous_root_entry_scripts_are_absent() -> None:
    project_root = Path(__file__).parents[1]

    assert not (project_root / "download_data.py").exists()
    assert not (project_root / "analysis.py").exists()
