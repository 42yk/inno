"""기상청 원본과 분석용 표준 컬럼 계약."""

SOURCE_COLUMN_MAP = {
    "지점": "station_id",
    "일시": "date",
    "평균기온(°C)": "avg_temp_c",
    "최저기온(°C)": "min_temp_c",
    "최고기온(°C)": "max_temp_c",
    "일강수량(mm)": "precipitation_mm",
    "평균 상대습도(%)": "avg_humidity_pct",
}

STANDARD_COLUMNS = [
    "station_id",
    "station_name",
    "date",
    "avg_temp_c",
    "min_temp_c",
    "max_temp_c",
    "precipitation_mm",
    "avg_humidity_pct",
]

NUMERIC_COLUMNS = [
    "avg_temp_c",
    "min_temp_c",
    "max_temp_c",
    "precipitation_mm",
    "avg_humidity_pct",
]

STATION_NAMES = {108: "서울"}
