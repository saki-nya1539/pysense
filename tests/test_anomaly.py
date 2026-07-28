import pandas as pd

from core.anomaly import detect_anomalies_isolation_forest, detect_anomalies_zscore


def _make_df():
    # 食費: 通常1000前後、1件だけ10000という明らかな異常値
    rows = []
    for i in range(10):
        rows.append({"date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i), "category": "食費", "amount": 1000 + i * 10, "description": "通常"})
    rows.append({"date": pd.Timestamp("2026-01-11"), "category": "食費", "amount": 10000, "description": "臨時"})
    return pd.DataFrame(rows)


def test_detect_anomalies_zscore_flags_large_outlier():
    df = _make_df()
    out = detect_anomalies_zscore(df)
    flagged = out[out["is_anomaly"]]
    assert len(flagged) >= 1
    assert 10000 in flagged["amount"].values


def test_detect_anomalies_zscore_skips_categories_with_too_few_rows():
    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-01-01")],
            "category": ["娯楽"],
            "amount": [5000],
            "description": ["映画"],
        }
    )
    out = detect_anomalies_zscore(df)
    assert out["is_anomaly"].sum() == 0
    assert out["z_score"].isna().all()


def test_detect_anomalies_isolation_forest_flags_outlier():
    df = _make_df()
    out = detect_anomalies_isolation_forest(df, contamination=0.1)
    flagged = out[out["is_anomaly"]]
    assert 10000 in flagged["amount"].values


def test_detect_anomalies_isolation_forest_handles_small_data():
    df = _make_df().head(3)
    out = detect_anomalies_isolation_forest(df)
    assert out["is_anomaly"].sum() == 0
