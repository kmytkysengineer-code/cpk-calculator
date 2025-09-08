#! /usr/bin/env python
# -*- coding: utf-8 -*-
import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cpk Calculator", page_icon="📈", layout="centered")

# -----------------
# ユーティリティ
# -----------------

def compute_cpk(mean: float, sigma: float, usl: float | None, lsl: float | None):
    """
    Cpk = min( (USL - mean) / (3*sigma), (mean - LSL) / (3*sigma) )
    片側しかない場合は、その側のみで計算。
    sigma は標本標準偏差（n-1）を想定。
    """
    if sigma is None or np.isnan(sigma) or sigma <= 0:
        return np.nan

    vals = []
    if usl is not None and not np.isnan(usl):
        vals.append((usl - mean) / (3.0 * sigma))
    if lsl is not None and not np.isnan(lsl):
        vals.append((mean - lsl) / (3.0 * sigma))
    if not vals:
        return np.nan
    return np.min(vals)


def summarize(values: np.ndarray):
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return {
            "count": 0,
            "mean": np.nan,
            "std": np.nan,
            "min": np.nan,
            "max": np.nan,
        }
    return {
        "count": arr.size,
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if arr.size > 1 else np.nan,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


# -----------------
# UI
# -----------------
st.title("📈 Cpk Calculator — 超速公開MVP")
st.caption("CSVアップロード or 値を直接入力 → Cpkを即時計算。")

method = st.radio(
    "入力方法を選択",
    ("CSVアップロード", "直接入力"),
    horizontal=True,
)

col_spec = st.columns(3)
with col_spec[0]:
    lsl = st.number_input("LSL (下限) — 任意", value=np.nan, placeholder="例: -0.30", format="%f")
with col_spec[1]:
    usl = st.number_input("USL (上限) — 任意", value=np.nan, placeholder="例: 0.30", format="%f")
with col_spec[2]:
    st.markdown("""
    <small>※ 片側のみでも計算可能です。</small>
    """, unsafe_allow_html=True)

if method == "CSVアップロード":
    st.subheader("CSVから計算")
    st.markdown("""
    - 測定値が **1列** に並んだCSVを想定（例：`value` 列）
    - ヘッダあり/なしを自動判定
    """)

    file = st.file_uploader("CSVファイルを選択", type=["csv"])
    if file is not None:
        data = file.read()
        # ヘッダあり・なしに柔軟対応
        try:
            df = pd.read_csv(io.BytesIO(data))
        except Exception:
            df = pd.read_csv(io.BytesIO(data), header=None)

        if df.shape[1] == 1:
            # 1列だけの場合、列名を value に
            df.columns = ["value"]
            column = "value"
        else:
            # 複数列ある場合は選択させる
            column = st.selectbox("どの列を測定値として使いますか？", options=list(df.columns))

        values = pd.to_numeric(df[column], errors="coerce").to_numpy()
        stats = summarize(values)

        st.write("### 概要")
        st.table(pd.DataFrame([stats]))

        cpk = compute_cpk(stats["mean"], stats["std"], usl, lsl)
        st.metric("Cpk", f"{cpk:.3f}" if pd.notna(cpk) else "計算不可")

        # ヒストグラム描画
        if stats["count"] > 0:
            st.write("### ヒストグラム")
            st.bar_chart(pd.DataFrame({"value": values}))

        # ダウンロード（結果）
        if stats["count"] > 0:
            res = pd.DataFrame([
                {
                    "count": stats["count"],
                    "mean": stats["mean"],
                    "std": stats["std"],
                    "min": stats["min"],
                    "max": stats["max"],
                    "LSL": lsl,
                    "USL": usl,
                    "Cpk": cpk,
                }
            ])
            st.download_button(
                "結果をCSVダウンロード",
                data=res.to_csv(index=False).encode("utf-8-sig"),
                file_name="cpk_result.csv",
                mime="text/csv",
            )
else:
    st.subheader("直接入力から計算")
    col = st.text_area(
        "測定値を改行/カンマ区切りで貼り付け",
        placeholder="例: 0.01, 0.02, -0.03, ...",
        height=120,
    )
    if st.button("計算する"):
        tokens = [t.strip() for t in col.replace("\n", ",").split(",") if t.strip()]
        values = pd.to_numeric(pd.Series(tokens), errors="coerce").to_numpy()
        stats = summarize(values)

        st.write("### 概要")
        st.table(pd.DataFrame([stats]))

        cpk = compute_cpk(stats["mean"], stats["std"], usl, lsl)
        st.metric("Cpk", f"{cpk:.3f}" if pd.notna(cpk) else "計算不可")

        if stats["count"] > 0:
            st.write("### ヒストグラム")
            st.bar_chart(pd.DataFrame({"value": values}))

# フッター
st.divider()
st.caption(
    "© Cpk Calculator MVP — このページは学習・検証用です。βテストのフィードバック歓迎。"
)
