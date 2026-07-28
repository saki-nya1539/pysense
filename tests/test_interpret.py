import pandas as pd

from core.forecast import ForecastResult, forecast_next_month, monthly_by_category, monthly_totals
from core.anomaly import detect_anomalies_zscore
from core.interpret import anomaly_summary_text, category_breakdown_text, forecast_interpretation


def test_anomaly_summary_text_no_anomalies():
    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-01-01")],
            "category": ["食費"],
            "amount": [1000],
            "description": ["昼食"],
            "is_anomaly": [False],
            "z_score": [0.1],
        }
    )
    text = anomaly_summary_text(df)
    assert "見つかりませんでした" in text


def test_anomaly_summary_text_with_anomalies():
    rows = []
    for i in range(10):
        rows.append({"date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i), "category": "食費", "amount": 1000, "description": "通常"})
    rows.append({"date": pd.Timestamp("2026-01-11"), "category": "食費", "amount": 10000, "description": "臨時"})
    df = pd.DataFrame(rows)
    flagged = detect_anomalies_zscore(df)
    text = anomaly_summary_text(flagged)
    assert "件の取引" in text
    assert "10,000" in text


def test_anomaly_summary_text_works_without_description_column():
    # 実機テストで発見: validate_and_prepareを通した実際のアプリのデータフレームには
    # description列が存在しないため、KeyErrorにならず動作することを確認する
    rows = []
    for i in range(10):
        rows.append({"date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i), "category": "食費", "amount": 1000})
    rows.append({"date": pd.Timestamp("2026-01-11"), "category": "食費", "amount": 10000})
    df = pd.DataFrame(rows)
    assert "description" not in df.columns

    flagged = detect_anomalies_zscore(df)
    text = anomaly_summary_text(flagged)
    assert "件の取引" in text
    assert "10,000" in text
    assert "（" not in text  # description用の括弧が付かないこと


def test_forecast_interpretation_describes_increasing_trend():
    result = ForecastResult(
        model="dummy", slope=5000, intercept=25000, r_squared=0.9,
        next_month=pd.Timestamp("2026-04-01"), predicted_total=45000, lower=40000, upper=50000,
    )
    text = forecast_interpretation(result)
    assert "増加" in text
    assert "45,000" in text


def test_forecast_interpretation_reports_insufficient_data():
    result = ForecastResult(
        model=None, slope=float("nan"), intercept=float("nan"), r_squared=float("nan"),
        next_month=None, predicted_total=float("nan"), lower=float("nan"), upper=float("nan"),
    )
    text = forecast_interpretation(result)
    assert "予測できません" in text


def test_category_breakdown_text_reports_top_category():
    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-01-05"), pd.Timestamp("2026-01-10")],
            "category": ["食費", "娯楽"],
            "amount": [5000, 1000],
        }
    )
    pivot = monthly_by_category(df)
    text = category_breakdown_text(pivot)
    assert "食費" in text
