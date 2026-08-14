"""
app.py
======
FinDash-VN — Dashboard thông tin đầu tư có hỗ trợ Chatbot.

Chạy: streamlit run app.py

Ba chế độ (sidebar):
    1) Một tài sản      -> Summary / Chart / Thống kê & Tài chính / Phân tích
    2) Danh mục đầu tư  -> CAPM / APT / Thống kê danh mục / Monte Carlo Simulation
    3) Chatbot          -> hỏi đáp với Claude, có ngữ cảnh từ dashboard
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import chatbot
import data_sources as ds
import portfolio_analytics as pa

st.set_page_config(page_title="FinDash-VN", layout="wide")


# =============================================================================
# Helpers dùng chung
# =============================================================================
def pick_symbol(asset_class: str, key_prefix: str):
    """Widget chọn mã theo loại tài sản. Trả về mã đã chọn (string)."""
    if asset_class == ds.ASSET_WORLD:
        options = ds.get_world_stock_list()
        default_idx = options.index("AAPL") if "AAPL" in options else 0
        return st.selectbox("Chọn mã cổ phiếu", options, index=default_idx, key=f"{key_prefix}_world")
    elif asset_class == ds.ASSET_VN:
        options = ds.get_vn_stock_list()
        default_idx = options.index("VNM") if "VNM" in options else 0
        return st.selectbox("Chọn mã cổ phiếu", options, index=default_idx, key=f"{key_prefix}_vn")
    else:
        crypto_map = ds.get_crypto_list()
        labels = [f"{sym} — {name}" for sym, name in crypto_map.items()]
        choice = st.selectbox("Chọn tiền điện tử", labels, key=f"{key_prefix}_crypto")
        return choice.split(" — ")[0]


def multi_pick_symbols(key_prefix: str):
    """Widget chọn nhiều mã thuộc nhiều loại tài sản khác nhau cho danh mục.
    Trả về list[(asset_class, symbol)]."""
    picked = []
    c1, c2, c3 = st.columns(3)
    with c1:
        world_syms = st.multiselect(
            "Cổ phiếu Thế giới", ds.get_world_stock_list(),
            default=["AAPL", "MSFT"], key=f"{key_prefix}_world_multi",
        )
        picked += [(ds.ASSET_WORLD, s) for s in world_syms]
    with c2:
        vn_syms = st.multiselect(
            "Cổ phiếu Việt Nam", ds.get_vn_stock_list(),
            default=["VNM"], key=f"{key_prefix}_vn_multi",
        )
        picked += [(ds.ASSET_VN, s) for s in vn_syms]
    with c3:
        crypto_map = ds.get_crypto_list()
        crypto_syms = st.multiselect(
            "Tiền điện tử", list(crypto_map.keys()),
            default=["BTC-USD"], key=f"{key_prefix}_crypto_multi",
        )
        picked += [(ds.ASSET_CRYPTO, s) for s in crypto_syms]
    return picked


def fmt(v):
    if isinstance(v, (int, float, np.floating, np.integer)):
        if abs(v) >= 1e9:
            return f"{v:,.0f}"
        return f"{v:,.4g}"
    return str(v)


# =============================================================================
# CHẾ ĐỘ 1 — MỘT TÀI SẢN
# =============================================================================
def render_single_asset_mode():
    st.sidebar.subheader("Chọn tài sản")
    asset_class = st.sidebar.selectbox("Loại tài sản", ds.ASSET_CLASSES, key="single_asset_class")
    symbol = pick_symbol(asset_class, "single")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "📈 Chart", "📊 Thống kê & Tài chính", "🔍 Phân tích"])

    with tab1:
        render_summary_tab(asset_class, symbol)
    with tab2:
        render_chart_tab(asset_class, symbol)
    with tab3:
        render_stats_financials_tab(asset_class, symbol)
    with tab4:
        render_analysis_tab(asset_class, symbol)


def render_summary_tab(asset_class, symbol):
    st.subheader(f"Summary — {symbol}")
    info = ds.get_summary_info(asset_class, symbol)
    if not info:
        st.info("Không có dữ liệu tóm tắt.")
    else:
        items = list(info.items())
        half = (len(items) + 1) // 2
        c1, c2 = st.columns(2)
        with c1:
            st.table(pd.DataFrame(items[:half], columns=["Chỉ tiêu", "Giá trị"]).set_index("Chỉ tiêu"))
        with c2:
            st.table(pd.DataFrame(items[half:], columns=["Chỉ tiêu", "Giá trị"]).set_index("Chỉ tiêu"))

    start, end = ds.period_to_dates("1 Năm")
    hist = ds.get_price_history(asset_class, symbol, start, end)
    if not hist.empty:
        fig = px.area(hist, x="Date", y="Close", title=f"Giá đóng cửa — {symbol} (1 năm gần nhất)")
        fig.update_xaxes(
            rangeselector=dict(buttons=list([
                dict(count=1, label="1T", step="month", stepmode="backward"),
                dict(count=3, label="3T", step="month", stepmode="backward"),
                dict(count=6, label="6T", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1N", step="year", stepmode="backward"),
                dict(label="Tất cả", step="all"),
            ]))
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Không lấy được dữ liệu giá lịch sử.")


def render_chart_tab(asset_class, symbol):
    st.subheader(f"Chart — {symbol}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        start_date = st.date_input("Từ ngày", datetime.today().date() - timedelta(days=180), key="chart_start")
    with c2:
        end_date = st.date_input("Đến ngày", datetime.today().date(), key="chart_end")
    with c3:
        sampling = st.selectbox("Sampling", ["Ngày", "Tuần", "Tháng"], key="chart_sampling")
    with c4:
        plot_type = st.selectbox("Loại biểu đồ", ["Line", "Candlestick"], key="chart_type")

    freq_map = {"Ngày": "D", "Tuần": "W", "Tháng": "ME"}
    raw = ds.get_price_history(asset_class, symbol, start_date, end_date)
    if raw.empty:
        st.warning("Không lấy được dữ liệu giá cho khoảng thời gian đã chọn.")
        return

    chart_df = ds.resample_ohlcv(raw, freq_map[sampling])
    chart_df["SMA20"] = chart_df["Close"].rolling(20).mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if plot_type == "Line":
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["Close"], mode="lines", name="Close"),
                       secondary_y=False)
    else:
        fig.add_trace(go.Candlestick(
            x=chart_df["Date"], open=chart_df["Open"], high=chart_df["High"],
            low=chart_df["Low"], close=chart_df["Close"], name="Candlestick",
        ), secondary_y=False)
    fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["SMA20"], mode="lines", name="SMA 20"),
                   secondary_y=False)
    fig.add_trace(go.Bar(x=chart_df["Date"], y=chart_df["Volume"], name="Volume", opacity=0.3),
                   secondary_y=True)
    fig.update_yaxes(range=[0, chart_df["Volume"].max() * 4], showticklabels=False, secondary_y=True)
    fig.update_layout(title=f"{symbol} — Biến động giá & khối lượng ({sampling.lower()})", height=550)
    st.plotly_chart(fig, use_container_width=True)


def render_stats_financials_tab(asset_class, symbol):
    st.subheader(f"Thống kê & Tài chính — {symbol}")

    start, end = ds.period_to_dates("1 Năm")
    hist = ds.get_price_history(asset_class, symbol, start, end)
    if not hist.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Giá gần nhất", fmt(hist.iloc[-1]["Close"]))
        c2.metric("Cao nhất 1N", fmt(hist["High"].max()))
        c3.metric("Thấp nhất 1N", fmt(hist["Low"].min()))
        ret_1y = hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1
        c4.metric("Lợi suất 1N", f"{ret_1y:.2%}")

    if asset_class == ds.ASSET_CRYPTO:
        st.info("Tiền điện tử không có báo cáo tài chính doanh nghiệp — chỉ hiển thị thống kê giá ở trên.")
        return

    st.markdown("#### Báo cáo tài chính")
    c1, c2 = st.columns(2)
    with c1:
        statement_label = st.selectbox(
            "Loại báo cáo", ["Kết quả kinh doanh", "Bảng cân đối kế toán", "Lưu chuyển tiền tệ"],
            key="fin_statement",
        )
    with c2:
        period_label = st.selectbox("Kỳ báo cáo", ["Năm", "Quý"], key="fin_period")

    statement_key = {"Kết quả kinh doanh": "income", "Bảng cân đối kế toán": "balance",
                      "Lưu chuyển tiền tệ": "cashflow"}[statement_label]
    period_key = {"Năm": "year", "Quý": "quarter"}[period_label]

    data = ds.get_financials(asset_class, symbol, statement_key, period_key)
    if data is None or data.empty:
        st.warning("Không có dữ liệu báo cáo tài chính cho lựa chọn này.")
    else:
        st.dataframe(data, use_container_width=True)


def render_analysis_tab(asset_class, symbol):
    st.subheader(f"Phân tích — {symbol}")
    if asset_class != ds.ASSET_WORLD:
        st.info(
            "Ước tính từ giới phân tích (Analyst Estimates) hiện chỉ khả dụng ổn định cho "
            "cổ phiếu thế giới trong bản demo này."
        )
        return
    analysis = ds.get_analyst_estimates(symbol)
    if not analysis:
        st.warning("Không lấy được dữ liệu phân tích.")
        return
    for name, df in analysis.items():
        st.markdown(f"**{name}**")
        st.dataframe(df, use_container_width=True)


# =============================================================================
# CHẾ ĐỘ 2 — DANH MỤC ĐẦU TƯ
# =============================================================================
def render_portfolio_mode():
    st.sidebar.subheader("Cấu hình danh mục")
    benchmark_class = st.sidebar.radio(
        "Benchmark CAPM/APT dùng chỉ số nào?",
        [ds.ASSET_WORLD, ds.ASSET_VN], key="bench_class",
        help="S&P500 nếu chọn Thế giới, VNINDEX nếu chọn Việt Nam.",
    )
    rf_pct = st.sidebar.number_input("Lãi suất phi rủi ro (%/năm)", 0.0, 20.0, 4.5, 0.1)
    rf_annual = rf_pct / 100
    period_label = st.sidebar.selectbox("Khoảng dữ liệu lịch sử", list(ds.PERIOD_DAYS.keys()), index=3)
    start, end = ds.period_to_dates(period_label)

    st.subheader("Chọn danh mục")
    picked = multi_pick_symbols("port")

    if len(picked) < 2:
        st.info("Chọn ít nhất 2 tài sản để phân tích danh mục.")
        return

    st.markdown("#### Tỉ trọng danh mục")
    weights = {}
    cols = st.columns(min(len(picked), 5))
    equal_w = round(100 / len(picked), 2)
    for i, (ac, sym) in enumerate(picked):
        with cols[i % len(cols)]:
            weights[f"{ac}:{sym}"] = st.number_input(
                f"{sym} (%)", 0.0, 100.0, equal_w, 0.5, key=f"w_{ac}_{sym}",
            )
    total_w = sum(weights.values())
    if total_w == 0:
        st.error("Tổng tỉ trọng phải > 0.")
        return
    norm_weights = np.array([w / total_w for w in weights.values()])
    st.caption(f"Tổng tỉ trọng nhập: {total_w:.1f}% → đã chuẩn hoá về 100%.")

    # Lấy dữ liệu giá & lợi suất cho từng tài sản
    returns_dict = {}
    for ac, sym in picked:
        hist = ds.get_price_history(ac, sym, start, end)
        if hist.empty or len(hist) < 30:
            st.warning(f"Bỏ qua {sym}: không đủ dữ liệu giá trong khoảng thời gian đã chọn.")
            continue
        returns_dict[f"{ac}:{sym}"] = pa.prices_to_returns(hist)

    if len(returns_dict) < 2:
        st.error("Không đủ dữ liệu để phân tích danh mục. Hãy chọn khoảng thời gian dài hơn.")
        return

    returns_df = pa.align_returns(returns_dict)
    valid_keys = list(returns_df.columns)
    norm_weights = np.array([weights[k] for k in valid_keys])
    norm_weights = norm_weights / norm_weights.sum()

    bench_hist = ds.get_benchmark_history(benchmark_class, start, end)
    bench_returns = pa.prices_to_returns(bench_hist) if not bench_hist.empty else pd.Series(dtype=float)

    tab_capm, tab_apt, tab_stats, tab_mc = st.tabs(
        ["📐 CAPM", "🧮 APT", "📊 Thống kê danh mục", "🎲 Monte Carlo Simulation"]
    )

    with tab_capm:
        render_capm_tab(returns_df, bench_returns, rf_annual, benchmark_class)
    with tab_apt:
        render_apt_tab(returns_df, benchmark_class, start, end, rf_annual)
    with tab_stats:
        port_stats = render_portfolio_stats_tab(returns_df, norm_weights, rf_annual, valid_keys)
        st.session_state["last_portfolio_stats"] = port_stats
        st.session_state["last_portfolio_tickers"] = valid_keys
    with tab_mc:
        render_monte_carlo_tab(returns_df, norm_weights, valid_keys)


def render_capm_tab(returns_df, bench_returns, rf_annual, benchmark_class):
    st.markdown(f"Mô hình CAPM — benchmark: **{benchmark_class}**, Rf = {rf_annual:.2%}/năm")
    if bench_returns.empty:
        st.warning("Không lấy được dữ liệu chỉ số benchmark.")
        return

    rows = []
    for col in returns_df.columns:
        res = pa.capm_analysis(returns_df[col], bench_returns, rf_annual)
        rows.append({
            "Tài sản": col, "Beta": res["beta"], "Alpha (năm)": res["alpha_annual"],
            "R²": res["r_squared"], "E[R] CAPM (năm)": res["expected_return_annual"],
        })
    res_df = pd.DataFrame(rows).set_index("Tài sản")
    st.dataframe(
        res_df.style.format({"Beta": "{:.2f}", "Alpha (năm)": "{:.2%}", "R²": "{:.2f}",
                              "E[R] CAPM (năm)": "{:.2%}"}),
        use_container_width=True,
    )

    fig = px.bar(res_df.reset_index(), x="Tài sản", y="Beta", title="Beta của từng tài sản so với benchmark")
    fig.add_hline(y=1, line_dash="dash", annotation_text="Beta thị trường = 1")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Đường thị trường chứng khoán (SML): E[R] = Rf + β × (E[Rm] − Rf). "
        "Beta > 1: biến động mạnh hơn thị trường; Beta < 1: biến động nhẹ hơn."
    )


def render_apt_tab(returns_df, benchmark_class, start, end, rf_annual):
    st.markdown("Mô hình APT (đa nhân tố) — hồi quy lợi suất từng tài sản theo nhiều nhân tố rủi ro.")

    if benchmark_class == ds.ASSET_WORLD:
        factor_tickers = {"Thị trường (S&P500)": "^GSPC", "Dầu thô (WTI)": "CL=F",
                           "Vàng": "GC=F", "Chỉ số USD": "DX-Y.NYB"}
    else:
        factor_tickers = {"Thị trường (VNINDEX)": None, "Vàng thế giới": "GC=F", "Dầu thô (WTI)": "CL=F"}

    chosen = st.multiselect(
        "Chọn nhân tố (factors)", list(factor_tickers.keys()),
        default=list(factor_tickers.keys())[:3], key="apt_factors",
    )
    if len(chosen) < 2:
        st.info("Chọn ít nhất 2 nhân tố để hồi quy APT.")
        return

    factor_series = {}
    for name in chosen:
        tk = factor_tickers[name]
        if tk is None:  # thị trường VN -> lấy VNINDEX qua benchmark helper
            bh = ds.get_benchmark_history(ds.ASSET_VN, start, end)
        else:
            bh = ds.get_price_history(ds.ASSET_WORLD, tk, start, end)
        if not bh.empty:
            factor_series[name] = pa.prices_to_returns(bh)

    if len(factor_series) < 2:
        st.warning("Không đủ dữ liệu nhân tố để hồi quy.")
        return

    factor_df = pa.align_returns(factor_series)

    rows, betas_table = [], {}
    for col in returns_df.columns:
        res = pa.apt_analysis(returns_df[col], factor_df, rf_annual)
        rows.append({"Tài sản": col, "Alpha (năm)": res["alpha_annual"], "R²": res["r_squared"],
                      "E[R] APT (năm)": res["expected_return_annual"]})
        betas_table[col] = res["betas"]

    st.markdown("**Beta theo từng nhân tố**")
    st.dataframe(pd.DataFrame(betas_table).T.style.format("{:.3f}"), use_container_width=True)

    st.markdown("**Kết quả hồi quy APT**")
    res_df = pd.DataFrame(rows).set_index("Tài sản")
    st.dataframe(
        res_df.style.format({"Alpha (năm)": "{:.2%}", "R²": "{:.2f}", "E[R] APT (năm)": "{:.2%}"}),
        use_container_width=True,
    )
    st.caption(
        "APT giả định lợi suất tài sản chịu ảnh hưởng bởi nhiều nhân tố rủi ro hệ thống "
        "(thay vì chỉ thị trường như CAPM). Đây là bản đơn giản hoá phục vụ mục đích học tập."
    )


def render_portfolio_stats_tab(returns_df, weights, rf_annual, keys):
    stats = pa.portfolio_stats(returns_df, weights, rf_annual)
    c1, c2, c3 = st.columns(3)
    c1.metric("Lợi suất kỳ vọng (năm)", f"{stats['expected_return_annual']:.2%}")
    c2.metric("Độ biến động (năm)", f"{stats['volatility_annual']:.2%}")
    c3.metric("Sharpe Ratio", f"{stats['sharpe_ratio']:.2f}")

    st.markdown("**Ma trận tương quan**")
    fig = px.imshow(stats["corr_matrix"], text_auto=".2f", color_continuous_scale="RdBu_r",
                     zmin=-1, zmax=1, title="Tương quan lợi suất giữa các tài sản")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Tỉ trọng danh mục**")
    w_df = pd.DataFrame({"Tài sản": keys, "Tỉ trọng": weights})
    st.plotly_chart(px.pie(w_df, names="Tài sản", values="Tỉ trọng", title="Phân bổ danh mục"),
                     use_container_width=True)
    return stats


def render_monte_carlo_tab(returns_df, weights, keys):
    c1, c2, c3 = st.columns(3)
    with c1:
        n_sims = st.selectbox("Số lượt mô phỏng (n)", [200, 500, 1000, 2000], index=1, key="mc_n")
    with c2:
        horizon = st.selectbox("Số ngày mô phỏng (t)", [30, 60, 90, 180], index=1, key="mc_t")
    with c3:
        confidence = st.selectbox("Độ tin cậy VaR", [0.90, 0.95, 0.99], index=1, key="mc_conf")

    initial_value = 100.0
    sim_paths, ending_values = pa.monte_carlo_portfolio(
        returns_df, weights, n_sims=n_sims, horizon_days=horizon, initial_value=initial_value,
    )

    fig = go.Figure()
    for i in range(min(n_sims, 300)):
        fig.add_trace(go.Scatter(y=sim_paths[i], mode="lines", line=dict(width=0.5),
                                  opacity=0.25, showlegend=False))
    fig.add_hline(y=initial_value, line_color="red",
                  annotation_text=f"Giá trị ban đầu = {initial_value:.0f}")
    fig.update_layout(title=f"Monte Carlo Simulation — Danh mục ({', '.join(keys)})",
                       xaxis_title="Ngày", yaxis_title="Giá trị danh mục", height=500)
    st.plotly_chart(fig, use_container_width=True)

    var_res = pa.value_at_risk(ending_values, initial_value, confidence)
    hist_fig = px.histogram(ending_values, nbins=50, title="Phân phối giá trị danh mục cuối kỳ")
    hist_fig.add_vline(x=var_res["threshold_value"], line_dash="dash", line_color="red",
                        annotation_text=f"Ngưỡng {int((1 - confidence) * 100)}th percentile")
    st.plotly_chart(hist_fig, use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric(f"Value at Risk (VaR) @ {int(confidence * 100)}%", f"{var_res['VaR']:.2f}")
    c2.metric(f"Conditional VaR (CVaR) @ {int(confidence * 100)}%", f"{var_res['CVaR']:.2f}")
    st.caption(
        "VaR: khoản lỗ tối đa kỳ vọng ở mức tin cậy đã chọn. "
        "CVaR (Expected Shortfall): mức lỗ trung bình trong các kịch bản tệ hơn VaR."
    )


# =============================================================================
# CHẾ ĐỘ 3 — CHATBOT
# =============================================================================
def render_chatbot_mode():
    st.subheader("💬 Chatbot hỗ trợ đầu tư")
    st.caption("Chatbot dùng Anthropic Claude API. Nhập API key của bạn để bắt đầu (chỉ lưu trong phiên làm việc).")

    api_key = st.sidebar.text_input("Anthropic API Key", type="password", key="anthropic_api_key")
    model = st.sidebar.text_input("Model", value=chatbot.DEFAULT_MODEL, key="anthropic_model")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    context = chatbot.build_context(
        asset_class=st.session_state.get("single_asset_class"),
        symbol=None,
        portfolio_tickers=st.session_state.get("last_portfolio_tickers"),
        port_stats=st.session_state.get("last_portfolio_stats"),
    )
    with st.expander("Ngữ cảnh hiện tại gửi kèm cho chatbot"):
        st.text(context)

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Hỏi chatbot về cổ phiếu, danh mục, CAPM, VaR...")
    if prompt:
        if not api_key:
            st.error("Vui lòng nhập Anthropic API Key ở sidebar trước.")
            return
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            client = chatbot.get_client(api_key)
            with st.chat_message("assistant"):
                with st.spinner("Đang trả lời..."):
                    reply = chatbot.ask_chatbot(client, st.session_state.chat_history, context, model=model)
                st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error(f"Lỗi khi gọi Claude API: {e}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    st.sidebar.title("📊 FinDash-VN")
    mode = st.sidebar.radio(
        "Chế độ", ["Một tài sản", "Danh mục đầu tư", "Chatbot"], key="app_mode",
    )
    st.sidebar.divider()

    st.title("FinDash-VN — Dashboard Thông Tin Đầu Tư")

    if mode == "Một tài sản":
        render_single_asset_mode()
    elif mode == "Danh mục đầu tư":
        render_portfolio_mode()
    else:
        render_chatbot_mode()


if __name__ == "__main__":
    main()
