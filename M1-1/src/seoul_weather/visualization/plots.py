"""서울 기온 분석 PNG 시각화."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from seoul_weather.analytics.anomalies import select_anomaly_annotations
from seoul_weather.analytics.statistics import fit_annual_linear_trend
from seoul_weather.errors import AnalysisValidationError
from seoul_weather.visualization.style import configure_plot_style, plt


VISUALIZATION_FILENAMES = (
    "01_annual_temperature_trend.png",
    "02_monthly_temperature_heatmap.png",
    "03_temperature_anomalies.png",
)


# 분석 결과로 세 PNG를 임시 생성한 뒤 검증해 최종 이름으로 저장한다.
def create_visualizations(
    annual: pd.DataFrame,
    monthly: pd.DataFrame,
    anomalies: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AnalysisValidationError(
            f"시각화 출력 디렉터리를 준비할 수 없습니다: {output_dir}"
        ) from exc
    use_korean = configure_plot_style()
    final_paths = [output_dir / filename for filename in VISUALIZATION_FILENAMES]
    temporary_paths = [
        output_dir / f".{filename}.part" for filename in VISUALIZATION_FILENAMES
    ]
    try:
        _plot_annual_temperature(annual, temporary_paths[0], use_korean)
        _plot_monthly_heatmap(monthly, temporary_paths[1], use_korean)
        _plot_temperature_anomalies(anomalies, temporary_paths[2], use_korean)
        for temporary_path in temporary_paths:
            if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                raise AnalysisValidationError(
                    f"시각화 파일 생성에 실패했습니다: {temporary_path.name}"
                )
        for temporary_path, final_path in zip(
            temporary_paths, final_paths, strict=True
        ):
            temporary_path.replace(final_path)
    except AnalysisValidationError:
        raise
    except OSError as exc:
        raise AnalysisValidationError(
            f"시각화 출력을 저장할 수 없습니다: {output_dir}"
        ) from exc
    finally:
        for temporary_path in temporary_paths:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    return final_paths


# 연평균·5년 이동평균·선형 추세를 한 그래프로 그린다.
def _plot_annual_temperature(
    annual: pd.DataFrame, output_path: Path, use_korean: bool
) -> None:
    labels = (
        {
            "title": "서울 연평균 기온 추세 (1994~2024)",
            "x": "연도",
            "y": "기온 (°C)",
            "annual": "연평균 기온",
            "rolling": "5년 후행 이동평균",
            "trend": "선형 추세",
        }
        if use_korean
        else {
            "title": "Seoul Annual Mean Temperature (1994–2024)",
            "x": "Year",
            "y": "Temperature (°C)",
            "annual": "Annual mean",
            "rolling": "5-year trailing mean",
            "trend": "Linear trend",
        }
    )
    valid = annual.dropna(subset=["avg_temp_c"])
    trend = fit_annual_linear_trend(annual)
    trend_values = trend["slope_c_per_year"] * valid["year"] + trend["intercept_c"]
    figure, axis = plt.subplots(figsize=(12, 7))
    axis.plot(
        valid["year"],
        valid["avg_temp_c"],
        marker="o",
        linewidth=1.4,
        color="#52789c",
        label=labels["annual"],
    )
    axis.plot(
        annual["year"],
        annual["rolling_5y_avg_c"],
        linewidth=3,
        color="#d4762c",
        label=labels["rolling"],
    )
    axis.plot(
        valid["year"],
        trend_values,
        linestyle="--",
        linewidth=2,
        color="#873d48",
        label=f"{labels['trend']} ({trend['slope_c_per_decade']:+.3f} °C/10y)",
    )
    annotation_indices = {
        valid.index[0],
        valid.index[-1],
        valid["avg_temp_c"].idxmax(),
        valid["avg_temp_c"].idxmin(),
    }
    for index in sorted(annotation_indices):
        row = valid.loc[index]
        axis.annotate(
            f"{int(row['year'])}: {row['avg_temp_c']:.2f}°C",
            (row["year"], row["avg_temp_c"]),
            xytext=(4, 8),
            textcoords="offset points",
            fontsize=8,
        )
    axis.set(title=labels["title"], xlabel=labels["x"], ylabel=labels["y"])
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(output_path, format="png", dpi=180, bbox_inches="tight")
    plt.close(figure)


# 연도·월별 평균기온 편차를 색상 히트맵으로 그린다.
def _plot_monthly_heatmap(
    monthly: pd.DataFrame, output_path: Path, use_korean: bool
) -> None:
    pivot = monthly.pivot(
        index="year", columns="month", values="monthly_anomaly_c"
    ).reindex(columns=range(1, 13))
    max_absolute = float(np.nanmax(np.abs(pivot.to_numpy(dtype=float))))
    color_limit = max(0.1, max_absolute)
    figure, axis = plt.subplots(figsize=(13, 9))
    image = axis.imshow(
        np.ma.masked_invalid(pivot.to_numpy(dtype=float)),
        aspect="auto",
        cmap="RdBu_r",
        vmin=-color_limit,
        vmax=color_limit,
        interpolation="nearest",
    )
    axis.set_xticks(np.arange(12), labels=[str(month) for month in range(1, 13)])
    axis.set_yticks(
        np.arange(len(pivot.index)), labels=[str(year) for year in pivot.index]
    )
    colorbar = figure.colorbar(image, ax=axis, pad=0.02)
    colorbar.set_label(
        "월 장기평균 대비 편차 (°C)"
        if use_korean
        else "Anomaly from monthly climatology (°C)"
    )
    axis.set(
        title=(
            "서울 연도·월별 평균기온 편차 (1994~2024)"
            if use_korean
            else "Seoul Monthly Mean Temperature Anomalies (1994–2024)"
        ),
        xlabel="월" if use_korean else "Month",
        ylabel="연도" if use_korean else "Year",
    )
    figure.tight_layout()
    figure.savefig(output_path, format="png", dpi=180, bbox_inches="tight")
    plt.close(figure)


# 월내 표준화 편차와 고온·저온 후보를 시계열로 그린다.
def _plot_temperature_anomalies(
    anomalies: pd.DataFrame, output_path: Path, use_korean: bool
) -> None:
    figure, axis = plt.subplots(figsize=(14, 7))
    axis.plot(
        anomalies["date"],
        anomalies["monthly_anomaly_z"],
        color="#888888",
        linewidth=0.45,
        alpha=0.7,
    )
    hot = anomalies.loc[anomalies["anomaly_category"] == "hot"]
    cold = anomalies.loc[anomalies["anomaly_category"] == "cold"]
    axis.scatter(
        hot["date"],
        hot["monthly_anomaly_z"],
        s=16,
        color="#c4473a",
        label="이상 고온 후보" if use_korean else "Hot candidates",
        zorder=3,
    )
    axis.scatter(
        cold["date"],
        cold["monthly_anomaly_z"],
        s=16,
        color="#32689a",
        label="이상 저온 후보" if use_korean else "Cold candidates",
        zorder=3,
    )
    axis.axhline(2.5, color="#c4473a", linestyle="--", linewidth=1)
    axis.axhline(-2.5, color="#32689a", linestyle="--", linewidth=1)
    annotation_rows = select_anomaly_annotations(anomalies, per_category=3)
    category_positions = {"hot": 0, "cold": 0}
    horizontal_offsets = (-32, 2, 30)
    for row in annotation_rows.itertuples(index=False):
        category = row.anomaly_category
        position = category_positions[category]
        category_positions[category] += 1
        axis.annotate(
            pd.Timestamp(row.date).strftime("%Y-%m-%d"),
            (row.date, row.monthly_anomaly_z),
            xytext=(
                horizontal_offsets[position % len(horizontal_offsets)],
                8 if category == "hot" else -15,
            ),
            textcoords="offset points",
            fontsize=7,
            horizontalalignment="center",
        )
    axis.set(
        title=(
            "서울 월내 표준화 기온 편차와 이상 기온 후보 (1994~2024)"
            if use_korean
            else "Seoul Standardized Daily Temperature Anomalies (1994–2024)"
        ),
        xlabel="날짜" if use_korean else "Date",
        ylabel="표준화 편차 (z)" if use_korean else "Standardized anomaly (z)",
    )
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(output_path, format="png", dpi=180, bbox_inches="tight")
    plt.close(figure)
