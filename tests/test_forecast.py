import pandas as pd

from core.forecast import forecast_next_month, monthly_by_category, monthly_totals


def _make_df():
    rows = []
    # 1月: 合計30000, 2月: 合計35000, 3月: 合計40000 (増加トレンド)
    for month, total in [(1, 30000), (2, 35000), (3, 40000)]:
        rows.append({"date": pd.Timestamp(f"2026-{month:02d}-15"), "category": "食費", "amount": total})
    return pd.DataFrame(rows)


def test_monthly_totals_aggregates_by_month():
    df = _make_df()
    monthly = monthly_totals(df)
    assert len(monthly) == 3
    assert monthly["total"].tolist() == [30000, 35000, 40000]


def test_monthly_by_category_aggregates_correctly():
    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-01-05"), pd.Timestamp("2026-01-10")],
            "category": ["食費", "娯楽"],
            "amount": [1000, 2000],
        }
    )
    pivot = monthly_by_category(df)
    assert len(pivot) == 2
    assert set(pivot["category"]) == {"食費", "娯楽"}


def test_forecast_next_month_predicts_increasing_trend():
    df = _make_df()
    monthly = monthly_totals(df)
    result = forecast_next_month(monthly)
    assert result.model is not None
    assert result.slope > 0
    assert result.predicted_total > 40000
    assert result.lower <= result.predicted_total <= result.upper


def test_forecast_next_month_returns_na_with_insufficient_data():
    monthly = pd.DataFrame({"month": [pd.Timestamp("2026-01-01")], "total": [10000]})
    result = forecast_next_month(monthly)
    assert result.model is None
    assert result.predicted_total != result.predicted_total  # NaN check
