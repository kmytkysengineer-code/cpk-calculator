#! /usr/bin/env python
# -*- coding: utf-8 -*-
import io
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Cpk Calculator｜無料で工程能力指数を算出",
    page_icon="📈",
    layout="centered",
)

# -----------------
# AdSense ヘルパー
# -----------------
ADS_CLIENT_ID = "ca-pub-PLACEHOLDER_CID"  # 例: ca-pub-1234567890...（審査通過後に差し替え）
ADS_SLOT_ID = "PLACEHOLDER_SLOT"          # 例: 1234567890（審査通過後に差し替え）


def show_ads(height: int = 180):
    """AdSense広告を埋め込む。審査通過後にIDを設定してください。"""
    adsense_code = f"""
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_CLIENT_ID}" crossorigin="anonymous"></script>
    <ins class="adsbygoogle" style="display:block" data-ad-client="{ADS_CLIENT_ID}" data-ad-slot="{ADS_SLOT_ID}" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
    """
    components.html(adsense_code, height=height)


# -----------------
# 計算ユーティリティ
# -----------------

def compute_cpk(mean: float, sigma: float, usl: float | None, lsl: float | None):
    """Cpk = min((USL-mean)/(3σ), (mean-LSL)/(3σ))。片側のみでも可。"""
    if sigma is None or np.isnan(sigma) or sigma <= 0:
        return np.nan
    vals = []
    if usl is not None and not (pd.isna(usl)):
        vals.append((usl - mean) / (3.0 * sigma))
    if lsl is not None and not (pd.isna(lsl)):
        vals.append((mean - lsl) / (3.0 * sigma))
    if not vals:
        return np.nan
    return float(np.min(vals))


def summarize(values: np.ndarray):
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return {"count": 0, "mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan}
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if arr.size > 1 else np.nan,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


# -----------------
# UI（ヘッダー）
# -----------------
st.title("📈 Cpk Calculator — 無料で工程能力指数を算出")
st.caption("値を直接入力 or CSVアップロード → Cpkを即時計算")

with st.expander("サンプルCSVをダウンロード"):
    sample = pd.DataFrame({"value": np.round(np.random.normal(loc=0.0, scale=0.1, size=150), 4)})
    st.download_button(
        "150件のサンプルCSVを取得",
        data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="sample_values.csv",
        mime="text/csv",
    )

# 序文直後に広告（審査通過後にIDをセット）
show_ads(height=180)

# -----------------
# 入力エリア
# -----------------
method = st.radio("入力方法を選択", ("直接入力", "CSVアップロード"), horizontal=True)
cols = st.columns(3)
with cols[0]:
    lsl = st.number_input("LSL (下限) — 任意", value=np.nan, placeholder="例: -0.30", format="%f")
with cols[1]:
    usl = st.number_input("USL (上限) — 任意", value=np.nan, placeholder="例: 0.30", format="%f")
with cols[2]:
    st.markdown("<small>※ 片側のみでも計算可能です</small>", unsafe_allow_html=True)

stats = None
values = None

if method == "CSVアップロード":
    st.subheader("CSVから計算")
    st.markdown("- 測定値が **1列** に並んだCSVを想定（例：`value` 列）\n- ヘッダあり/なしを自動判定")
    file = st.file_uploader("CSVファイルを選択", type=["csv"])
    if file is not None:
        data = file.read()
        try:
            df = pd.read_csv(io.BytesIO(data))
        except Exception:
            df = pd.read_csv(io.BytesIO(data), header=None)
        if df.shape[1] == 1:
            df.columns = ["value"]
            column = "value"
        else:
            column = st.selectbox("どの列を測定値として使いますか？", options=list(df.columns))
        values = pd.to_numeric(df[column], errors="coerce").to_numpy()
        stats = summarize(values)
else:
    st.subheader("直接入力から計算")
    raw = st.text_area("測定値を改行/カンマ区切りで貼り付け", placeholder="例: 0.01, 0.02, -0.03, ...", height=120)
    if st.button("計算する"):
        tokens = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
        values = pd.to_numeric(pd.Series(tokens), errors="coerce").to_numpy()
        stats = summarize(values)

# -----------------
# 結果表示
# -----------------
if stats is not None:
    st.write("### 概要")
    st.table(pd.DataFrame([stats]))
    cpk = compute_cpk(stats["mean"], stats["std"], usl, lsl)
    st.metric("Cpk", f"{cpk:.3f}" if pd.notna(cpk) else "計算不可")

    # ヒストグラム（Altair）+ USL/LSL/mean の縦線
    if stats["count"] > 0:
        hist_df = pd.DataFrame({"value": values})
        bins = max(10, min(50, int(np.sqrt(max(1, stats["count"])))))
        base = alt.Chart(hist_df).mark_bar().encode(
            x=alt.X("value:Q", bin=alt.Bin(maxbins=bins), title="Value"),
            y=alt.Y("count():Q", title="Count"),
        )
        overlays = []
        if pd.notna(usl):
            overlays.append(alt.Chart(pd.DataFrame({"x": [usl]})).mark_rule().encode(x="x:Q"))
        if pd.notna(lsl):
            overlays.append(alt.Chart(pd.DataFrame({"x": [lsl]})).mark_rule().encode(x="x:Q"))
        if pd.notna(stats["mean"]):
            overlays.append(alt.Chart(pd.DataFrame({"x": [stats["mean"]]})).mark_rule().encode(x="x:Q"))
        chart = base
        for r in overlays:
            chart = chart + r
        st.altair_chart(chart.interactive(), use_container_width=True)

        # 結果ダウンロード
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

# 本文途中に広告（審査通過後にIDをセット）
show_ads(height=180)

# -----------------
# 解説記事（SEO用）
# -----------------
st.header("Cpkとは？")
st.markdown(
    """
Cpk（工程能力指数、Process Capability Index）は、製造業において工程が規格範囲内に収まっているかを評価するための代表的な統計指標です。製品や部品の寸法や性能が、設定された上限値（USL）と下限値（LSL）の間にどの程度安定して収まっているかを数値で表します。工程の安定度やばらつきの大きさを定量的に把握できるため、品質保証や工程改善の現場で広く用いられています。
    """
)

st.header("CpとCpkの違い")
st.markdown(
    """
品質管理では **Cp** と **Cpk** という2つの指標がよく登場します。\\
- **Cp**：工程のばらつき（標準偏差）と規格幅を比較した指標。工程の「潜在能力」を評価できます。ただし、工程の平均値が規格の中央からズレている場合は反映されません。\\
- **Cpk**：Cpに工程平均の偏りを加味した指標。実際に製品が規格を満たしている度合いをより現実的に表します。\\
そのため、Cpが高くても平均値が偏っているとCpkは低くなり、不良品が発生しやすい工程だと判断されます。Cpkはより実務的な「工程の合格度」を示す指標です。
    """
)

st.header("Cpkの基準値")
st.markdown(
    """
一般的な業界で用いられる目安は以下の通りです。\\
- **Cpk ≥ 1.67** … 十分に安定した工程\\
- **Cpk ≥ 1.33** … 合格基準（量産に適している）\\
- **Cpk ≥ 1.00** … ぎりぎり合格（改善の余地あり）\\
- **Cpk < 1.00** … 工程改善が必要\\
業界や顧客の要求によって基準は異なりますが、量産製造においては **1.33以上** が目標値とされることが多いです。
    """
)

# 記事中間に広告
show_ads(height=180)

st.header("このアプリの使い方")
st.markdown(
    """
本アプリは、Cpkを手軽にオンラインで計算できる無料ツールです。使い方はシンプルで、以下の手順で実行できます。\\
1. **測定値を入力** — CSVファイルをアップロードするか、数値を直接入力してください。\\
2. **規格値を入力** — 上限値（USL）、下限値（LSL）を入力します。片側だけでも計算可能です。\\
3. **計算実行** — 「計算する」ボタンを押すと、平均値・標準偏差・最小値・最大値などの統計量と、Cpkの計算結果が表示されます。\\
4. **結果の活用** — 計算結果はCSV形式でダウンロードできるため、レポートや社内資料にも簡単に転用可能です。
    """
)

st.header("よくある質問（FAQ）")
st.markdown(
    """
**Q. CpとCpkのどちらを使えば良いですか？**\\
A. 工程の潜在能力を確認するならCp、実際の合格度を評価するならCpkです。通常はCpkが品質保証の判断基準になります。\\\n\n
**Q. 測定値が全て同じ場合はどうなりますか？**\\
A. 標準偏差が0となるため、Cpkは計算できません。この場合は工程が安定しすぎているか、測定データの取り方を見直す必要があります。\\\n\n
**Q. 規格値が片側しかない場合は？**\\
A. 入力された側だけを用いてCpkを算出します。
    """
)

# ページ末尾に広告
show_ads(height=180)

st.divider()
with st.expander("アプリについて / 免責・お問い合わせ"):
    st.markdown(
        """
- 本アプリはCpkの簡易計算ツールです。正式な品質判定は社内規程・顧客規格に従ってください。\\
- 入力データはブラウザ内で処理されます（保存機能は未実装）。\\
- Google AdSenseのポリシーに準拠して運用しています。\\
- 改善要望・お問い合わせはこちら: [Googleフォーム](https://example.com/contact)
        """
    )

st.caption("© Cpk Calculator — 学習・検証用 β")

