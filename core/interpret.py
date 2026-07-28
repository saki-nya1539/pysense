"""core/interpret.py

分析結果を平易な日本語の解説文に変換する。
"""

from __future__ import annotations

import pandas as pd

from core.forecast import ForecastResult


def anomaly_summary_text(anomalies: pd.DataFrame) -> str:
    flagged = anomalies[anomalies["is_anomaly"]]
    if len(flagged) == 0:
        return "この期間の取引データに、目立った異常支出は見つかりませんでした。"

    lines = [f"{len(flagged)}件の取引が、通常より大きく外れた支出として検出されました。"]
    top = flagged.sort_values("amount", ascending=False).head(3)
    for _, row in top.iterrows():
        date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        # descriptionはCSVによっては存在しない列のため、無い場合は省略する
        # （実機テストで発見: validate_and_prepareがdate/category/amountの3列に
        #   正規化する際にdescription列が失われ、KeyErrorになっていた不具合の再発防止）
        description = row["description"] if "description" in row.index and pd.notna(row["description"]) else None
        if description:
            lines.append(f"・{date_str}　{row['category']}　¥{row['amount']:,.0f}（{description}）")
        else:
            lines.append(f"・{date_str}　{row['category']}　¥{row['amount']:,.0f}")
    return "\n".join(lines)


def forecast_interpretation(result: ForecastResult) -> str:
    if result.model is None:
        return "月次データが2か月分未満のため、来月の支出を予測できません。データが増えると予測できるようになります。"

    trend_word = "増加" if result.slope >= 0 else "減少"
    month_str = result.next_month.strftime("%Y年%m月") if result.next_month is not None else "来月"

    return (
        f"月ごとの支出は1か月あたり平均{abs(result.slope):,.0f}円のペースで{trend_word}しています"
        f"（決定係数R² = {result.r_squared:.3f}）。\n"
        f"このペースが続いた場合、{month_str}の支出合計は約{result.predicted_total:,.0f}円と予測されます"
        f"（95%予測区間: {result.lower:,.0f}〜{result.upper:,.0f}円）。"
    )


def category_breakdown_text(monthly_category: pd.DataFrame) -> str:
    if len(monthly_category) == 0:
        return "カテゴリ別の集計データがありません。"

    latest_month = monthly_category["month"].max()
    latest = monthly_category[monthly_category["month"] == latest_month]
    latest = latest.sort_values("amount", ascending=False)

    if len(latest) == 0:
        return "直近月のカテゴリ別データがありません。"

    top = latest.iloc[0]
    total = latest["amount"].sum()
    share = (top["amount"] / total * 100) if total > 0 else 0

    return (
        f"{latest_month.strftime('%Y年%m月')}の支出は「{top['category']}」が最も多く、"
        f"¥{top['amount']:,.0f}（全体の{share:.1f}%）を占めています。"
    )
