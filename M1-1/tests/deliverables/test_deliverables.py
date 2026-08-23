from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).parents[2]
SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "analysis_summary.json"
README_PATH = PROJECT_ROOT / "README.md"
REPORT_PATH = PROJECT_ROOT / "REPORT.md"
GLOSSARY_PATH = PROJECT_ROOT / "docs" / "learning" / "glossary.md"
REQUIRED_IMAGES = [
    "01_annual_temperature_trend.png",
    "02_monthly_temperature_heatmap.png",
    "03_temperature_anomalies.png",
]


def load_summary() -> dict[str, object]:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_readme_and_report_include_verified_core_statistics() -> None:
    summary = load_summary()
    readme = README_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    quality = summary["data_quality"]
    trend = summary["trend"]
    extremes = summary["extremes"]

    expected_values = [
        f"{quality['row_count']:,}",
        f"{trend['slope_c_per_decade']:+.3f}",
        f"{trend['difference_c']:.2f}",
        f"{extremes['warmest_year_mean_c']:.2f}",
        str(extremes["hot_candidate_count"]),
        str(extremes["cold_candidate_count"]),
    ]
    for value in expected_values:
        assert value in readme
        assert value in report


def test_readme_and_report_include_temperature_missing_counts_and_rates() -> None:
    summary = load_summary()
    readme = README_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")
    quality = summary["data_quality"]
    labels = {
        "avg_temp_c": "평균기온",
        "min_temp_c": "최저기온",
        "max_temp_c": "최고기온",
    }

    for column, label in labels.items():
        count = quality["missing_counts"][column]
        rate = quality["missing_rates_pct"][column]
        expected = f"| {label} 결측 | {count:,}건 ({rate:.4f}%)"
        assert expected in readme
        assert expected in report


def test_readme_and_report_reference_all_generated_images() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    report = REPORT_PATH.read_text(encoding="utf-8")

    for image_name in REQUIRED_IMAGES:
        relative_path = f"images/{image_name}"
        assert relative_path in readme
        assert relative_path in report
        image_path = PROJECT_ROOT / relative_path
        with Image.open(image_path) as image:
            assert image.format == "PNG"
            image.verify()


def test_report_contains_required_analysis_and_transparency_sections() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    required_headings = [
        "## 1. 분석 주제 및 선정 이유",
        "## 2. 분석 질문",
        "## 3. 데이터 설명",
        "## 4. 데이터 정제",
        "## 5. 분석 방법",
        "## 6. 분석 결과 및 시각화",
        "## 7. 인사이트",
        "## 8. 결론 및 한계점",
        "## 9. 재현 방법",
        "## 10. AI 사용 로그",
    ]
    for heading in required_headings:
        assert heading in report
    for label in [
        "관찰(Fact)",
        "해석(Interpretation)",
        "한계(Limit)",
        "행동(Action)",
    ]:
        assert report.count(label) >= 3
    assert "가설(Hypothesis)" in report
    assert "해석(Hypothesis)" not in report
    for ai_item in ["사용 작업", "사용 이유", "검증 방법", "사람의 최종 판단"]:
        assert ai_item in report


def test_glossary_covers_required_data_analysis_and_time_series_terms() -> None:
    glossary = GLOSSARY_PATH.read_text(encoding="utf-8")
    required_headings = [
        "### 결측치",
        "### 이상치",
        "### 이상 기온",
        "### 통계적 이상 기온",
        "### 트렌드",
        "### 계절성",
        "### 노이즈",
        "### 이동평균",
        "### 변화량",
        "### 관찰",
        "### 해석",
    ]

    for heading in required_headings:
        assert heading in glossary


def test_glossary_headings_include_english_terms() -> None:
    glossary = GLOSSARY_PATH.read_text(encoding="utf-8")
    term_headings = [
        line
        for line in glossary.splitlines()
        if line.startswith("### ")
    ]

    assert len(term_headings) == 52
    assert all(" (" in heading and heading.endswith(")") for heading in term_headings)

    required_bilingual_terms = [
        "### 결측치 (Missing Value)",
        "### 이상치 (Outlier)",
        "### 통계적 이상 기온 (Statistical Temperature Anomaly)",
        "### 이동평균 (Moving Average)",
        "### 표준화 편차 (Standardized Deviation, Z-score)",
        "### 관찰 (Observation)",
        "### 인과관계 (Causality)",
    ]
    for heading in required_bilingual_terms:
        assert heading in term_headings


def test_public_markdown_avoids_unsupported_bold_syntax() -> None:
    assert not (PROJECT_ROOT / "docs" / "superpowers").exists()

    expected_docs = {
        Path("README.md"),
        Path("requirements/README.md"),
        Path("design/data-source.md"),
        Path("design/analysis-design.md"),
        Path("design/architecture.md"),
        Path("design/implementation-plan.md"),
        Path("guides/manual-data-input.md"),
        Path("guides/verification-plan.md"),
        Path("learning/guide.md"),
        Path("learning/objectives.md"),
        Path("learning/glossary.md"),
    }
    actual_docs = {
        path.relative_to(PROJECT_ROOT / "docs")
        for path in (PROJECT_ROOT / "docs").rglob("*.md")
    }
    assert actual_docs == expected_docs

    public_markdown = [
        README_PATH,
        REPORT_PATH,
        *sorted((PROJECT_ROOT / "docs").rglob("*.md")),
    ]

    for path in public_markdown:
        content = path.read_text(encoding="utf-8")
        assert "**" not in content, f"지원하지 않는 강조 문법: {path}"


def test_readme_links_to_final_report_and_uses_actual_result_heading() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "[전체 분석 리포트](REPORT.md)" in readme
    assert "## 실제 분석 결과" in readme
    assert "아직 실제 분석" not in readme


def test_learning_guide_covers_project_data_analysis_concepts() -> None:
    guide_path = PROJECT_ROOT / "docs" / "learning" / "guide.md"
    guide = guide_path.read_text(encoding="utf-8")
    required_headings = [
        "## 1. 데이터 분석이 필요한 이유",
        "## 2. 데이터 구조",
        "## 3. 데이터 품질",
        "## 4. 기초 통계",
        "## 5. 시계열 분석",
        "## 6. 통계적 이상 기온",
        "## 7. 결과 해석",
        "## 8. 재현성과 추적 가능성",
    ]
    for heading in required_headings:
        assert heading in guide

    required_concepts = [
        "결측치",
        "이상치",
        "관측률",
        "이동평균",
        "z 점수",
        "관찰",
        "인과관계",
    ]
    for concept in required_concepts:
        assert concept in guide

    requirements = (
        PROJECT_ROOT / "docs" / "requirements" / "README.md"
    ).read_text(
        encoding="utf-8"
    )
    glossary = GLOSSARY_PATH.read_text(encoding="utf-8")
    objectives = (
        PROJECT_ROOT / "docs" / "learning" / "objectives.md"
    ).read_text(encoding="utf-8")
    analysis_design = (
        PROJECT_ROOT / "docs" / "design" / "analysis-design.md"
    ).read_text(encoding="utf-8")
    subject = (PROJECT_ROOT / "subject.md").read_text(encoding="utf-8")
    terminology_contract = [
        "관찰은 데이터와 그래프에서 직접 확인할 수 있는 사실과 패턴이다.",
        "해석은 관찰이 무엇을 의미하는지 설명하는 판단이다.",
        "가설은 관찰의 가능한 원인을 설명하며 추가 자료로 검증해야 하는 주장이다.",
    ]
    for statement in terminology_contract:
        assert statement in requirements
        assert statement in glossary
        assert statement in guide
        assert statement in objectives
    assert "해석(Interpretation)" in analysis_design
    assert "가설(Hypothesis)" in analysis_design
    assert "해석(Hypothesis)" not in analysis_design
    assert "관찰(Fact)" in subject
    assert "해석(Interpretation)" in subject
    assert "가설(Hypothesis)" in subject
    assert "해석(가설)" not in subject

    assert "## 1. 데이터를 분석한다는 것" not in guide
    assert "### 1.1 데이터에서 필요한 패턴을 찾는다" in guide
    assert "### 1.1 많은 값에서 필요한 패턴을 찾는다" not in guide
    assert "| 질문 | 필요한 관점 |" in guide
    assert "| 알고 싶은 것 | 필요한 관점 |" not in guide
    assert "데이터는 현실에서 측정하거나 수집한 값을 정리한 것이다." in guide
    assert "데이터는 관측한 사실의 기록이다." not in guide
    assert "| 개념 | 의미 | 판정 근거 | 분석 관점 |" in guide
    assert "| 개념 | 뜻 | 분석에서의 태도 |" not in guide
    assert "이상치는 값이 분포에서 얼마나 떨어져 있는지를 설명한다." in guide
    assert "오류 데이터는 값이 믿을 만한지를 판단한 결과다." in guide
    assert (
        "이상 기온은 품질검사를 통과한 실제 기온이 평소와 크게 다른 현상이다."
        in guide
    )

    readme = README_PATH.read_text(encoding="utf-8")
    docs_index = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "[데이터 분석 개념 학습 가이드](docs/learning/guide.md)" in readme
    assert "[데이터 분석 개념 학습 가이드](learning/guide.md)" in docs_index
