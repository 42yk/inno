"""시계열 분석에 공통으로 사용하는 파생 변수."""

import pandas as pd


SEASON_BY_MONTH = {
    1: "겨울",
    2: "겨울",
    3: "봄",
    4: "봄",
    5: "봄",
    6: "여름",
    7: "여름",
    8: "여름",
    9: "가을",
    10: "가을",
    11: "가을",
    12: "겨울",
}


# 날짜에서 연·월·계절을 파생하고 일교차와 30일 이동평균을 추가한다.
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    featured = df.copy()
    featured["date"] = pd.to_datetime(featured["date"], errors="raise")
    featured = featured.sort_values("date").reset_index(drop=True)
    featured["year"] = featured["date"].dt.year
    featured["month"] = featured["date"].dt.month
    featured["season"] = featured["month"].map(SEASON_BY_MONTH)
    featured["daily_range_c"] = featured["max_temp_c"] - featured["min_temp_c"]
    featured["rolling_30d_avg_c"] = featured["avg_temp_c"].rolling(
        window=30, min_periods=24
    ).mean()
    return featured
