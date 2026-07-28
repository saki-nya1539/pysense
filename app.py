"""app.py

PySense - 支出異常検知・予測付き家計簿アプリ
Streamlit + pandas + scikit-learn

サイドバーでCSVをアップロード(またはサンプルデータを使用)し、
日付・カテゴリ・金額の列を選択して「分析を実行」を押すと、
支出トレンド・異常検知・来月の支出予測が確認できる。
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.anomaly import detect_anomalies_isolation_forest, detect_anomalies_zscore
from core.data_ingest import guess_columns, read_transactions_csv, validate_and_prepare
from core.forecast import forecast_next_month, monthly_by_category, monthly_totals
from core.interpret import anomaly_summary_text, category_breakdown_text, forecast_interpretation
from core.sample_data import generate_sample_transactions

st.set_page_config(page_title="PySense - 家計改善AIアプリ", layout="wide")

if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "prepared_df" not in st.session_state:
    st.session_state.prepared_df = None
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False


def _load_sample():
    st.session_state.raw_df = generate_sample_transactions()


with st.sidebar:
    st.header("データ")
    uploaded = st.file_uploader("CSVファイルをアップロード", type=["csv"])
    if st.button("サンプルデータを使う", use_container_width=True):
        _load_sample()

    if uploaded is not None:
        try:
            st.session_state.raw_df = read_transactions_csv(uploaded)
        except Exception as e:  # noqa: BLE001
            st.error(f"CSVの読み込みに失敗しました: {e}")

    raw_df = st.session_state.raw_df

    date_col = category_col = amount_col = None
    if raw_df is not None:
        guess = guess_columns(raw_df)
        columns = list(raw_df.columns)

        st.divider()
        date_col = st.selectbox("日付列", columns, index=columns.index(guess.date_col) if guess.date_col in columns else 0)
        category_col = st.selectbox("カテゴリ列", columns, index=columns.index(guess.category_col) if guess.category_col in columns else 0)
        amount_col = st.selectbox("金額列", columns, index=columns.index(guess.amount_col) if guess.amount_col in columns else 0)

        st.divider()
        method = st.selectbox("異常検知の手法", ["z-score（統計的）", "Isolation Forest（機械学習）"])
        st.session_state.anomaly_method = method

        run = st.button("▶ 分析を実行", type="primary", use_container_width=True)
        if run:
            try:
                prepared = validate_and_prepare(raw_df, date_col, category_col, amount_col)
                st.session_state.prepared_df = prepared
                st.session_state.analyzed = True
            except Exception as e:  # noqa: BLE001
                st.error(f"分析に失敗しました: {e}")

st.title("PySense - 支出異常検知・予測付き家計簿")

tab1, tab2, tab3, tab4 = st.tabs(["データプレビュー", "支出トレンド", "異常検知", "来月の支出予測"])

with tab1:
    if st.session_state.raw_df is None:
        st.info("サイドバーからCSVをアップロードするか、「サンプルデータを使う」を押してください。")
    else:
        st.subheader("アップロードデータ（先頭50行）")
        st.dataframe(st.session_state.raw_df.head(50), use_container_width=True)

if not st.session_state.analyzed or st.session_state.prepared_df is None:
    with tab2, tab3, tab4:
        st.info("左側で列を選択し、「分析を実行」を押してください。")
else:
    df = st.session_state.prepared_df
    monthly = monthly_totals(df)
    monthly_cat = monthly_by_category(df)

    with tab2:
        st.subheader("月別支出の推移")
        fig = px.line(monthly, x="month", y="total", markers=True)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("カテゴリ別支出（月別・積み上げ）")
        fig2 = px.bar(monthly_cat, x="month", y="amount", color="category")
        st.plotly_chart(fig2, use_container_width=True)

        st.info(category_breakdown_text(monthly_cat))

    with tab3:
        method = st.session_state.get("anomaly_method", "z-score（統計的）")
        if method.startswith("z-score"):
            flagged = detect_anomalies_zscore(df)
        else:
            flagged = detect_anomalies_isolation_forest(df)

        st.subheader("異常検知の結果")
        st.info(anomaly_summary_text(flagged))

        anomalies_only = flagged[flagged["is_anomaly"]].sort_values("amount", ascending=False)
        if len(anomalies_only) > 0:
            st.dataframe(anomalies_only, use_container_width=True)

        # descriptionはCSVによっては存在しない列のため、あるときだけhover_dataに含める
        hover_cols = ["category"] + (["description"] if "description" in flagged.columns else [])
        fig3 = px.scatter(
            flagged, x="date", y="amount", color="is_anomaly",
            hover_data=hover_cols,
            color_discrete_map={True: "#DC2626", False: "#4F46E5"},
        )
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        result = forecast_next_month(monthly)
        st.subheader("来月の支出予測")
        st.info(forecast_interpretation(result))

        if result.model is not None:
            future_row = pd.DataFrame({"month": [result.next_month], "total": [result.predicted_total]})
            combined = pd.concat([monthly.assign(kind="実績"), future_row.assign(kind="予測")])
            fig4 = px.line(combined, x="month", y="total", color="kind", markers=True)
            st.plotly_chart(fig4, use_container_width=True)
