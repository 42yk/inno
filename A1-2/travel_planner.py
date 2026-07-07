from __future__ import annotations

import argparse
from datetime import datetime

from config import ConfigError, load_settings
from gemini_client import GeminiError, build_fallback_report, generate_recommendation, generate_report
from kakao_client import search_restaurants
from result_writer import save_raw_data, save_report


# CLI 입력 날짜가 YYYY-MM-DD 형식인지 검증합니다.
def parse_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 형식이어야 합니다.") from error
    return value


# argparse 기반 CLI 옵션을 정의하고 파싱합니다.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gemini와 Kakao Local API를 조합한 국내 여행 추천 CLI")
    parser.add_argument(
        "-date",
        "--date",
        dest="date",
        required=True,
        type=parse_date,
        help='여행 날짜. 예: -date "2026-03-15"',
    )
    return parser.parse_args()


# 원본 JSON 저장용 데이터를 과제 요구 스키마에 맞게 조립합니다.
def build_raw_data(date: str, recommendation: dict, restaurants: list[dict], errors: list[dict]) -> dict:
    return {
        "date": date,
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }


# 날짜 하나에 대한 추천, 맛집 검색, 리포트 저장 흐름을 실행합니다.
def run(date: str) -> int:
    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"[오류] {error}")
        return 1

    errors: list[dict] = []

    print("[1/3] 1차 추천 생성 중(Gemini)...")
    try:
        recommendation = generate_recommendation(date, settings)
    except GeminiError as error:
        print(f"  - 오류: {error}")
        return 1

    recommended_city = recommendation["recommended_city"]
    print(f"  - recommended_city: {recommended_city}")

    print("[2/3] 맛집 검색 중(Kakao Local)...")
    restaurants = search_restaurants(recommended_city, settings, errors, size=5)
    if restaurants:
        print(f"  - 맛집 {len(restaurants)}곳 검색 완료")
    else:
        print("  - 맛집 데이터 없음. 리포트 생성을 계속 진행합니다.")

    print("[3/3] 최종 리포트 생성 중(Gemini)...")
    try:
        report = generate_report(date, recommendation, restaurants, errors, settings)
        print("  - 리포트 생성 완료")
    except GeminiError as error:
        errors.append(
            {
                "step": "report_generation",
                "type": "REPORT_GENERATION_ERROR",
                "message": str(error),
            }
        )
        report = build_fallback_report(date, recommendation, restaurants, errors)
        print("  - Gemini 리포트 생성 실패. 로컬 fallback 리포트를 저장합니다.")

    raw_data = build_raw_data(date, recommendation, restaurants, errors)
    raw_path = save_raw_data(date, raw_data)
    report_path = save_report(date, report)

    print("\n완료!")
    print(f"- 원본 데이터: {raw_path}")
    print(f"- 여행 리포트: {report_path}")
    return 0


# 스크립트 진입점에서 인자를 읽고 실행 결과 코드를 반환합니다.
def main() -> int:
    args = parse_args()
    return run(args.date)


if __name__ == "__main__":
    raise SystemExit(main())
