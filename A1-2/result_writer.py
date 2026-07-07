from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"


# results 폴더를 만들고 원본 데이터를 JSON 파일로 저장합니다.
def save_raw_data(date: str, data: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"{date}_raw.json"
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


# results 폴더를 만들고 최종 여행 리포트를 Markdown 파일로 저장합니다.
def save_report(date: str, markdown: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"{date}_travel_plan.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
