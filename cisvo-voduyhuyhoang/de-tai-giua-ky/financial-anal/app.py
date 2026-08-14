"""
app.py
======
FinDash-VN — Dashboard thông tin đầu tư có hỗ trợ Chatbot.

Chạy: streamlit run app.py

Tính năng chính:
    - Multipage app thật (st.navigation/st.Page): Một tài sản / Danh mục đầu tư / Chatbot
    - Cổng đăng nhập tuỳ chọn (auth.py: none / password / Google OIDC)
    - Theme tối + logo riêng (.streamlit/config.toml, assets/logo.png)
    - st.fragment cho các phần nặng (chart, CAPM/APT, Monte Carlo) -> đổi input
      không phải rerun toàn trang
    - Auto-refresh giá theo chu kỳ (st.fragment run_every, có thể bật/tắt)
    - st.dialog: xem nhanh 1 mã khác không cần rời trang
    - st.status: hiển thị tiến trình khi tải & phân tích dữ liệu danh mục
    - st.data_editor: chỉnh tỉ trọng danh mục ngay trong bảng
    - st.file_uploader: nạp danh mục có sẵn từ file CSV
    - Xuất báo cáo CSV / Excel / PDF
    - Bảng dữ liệu nâng cao qua streamlit-aggrid (tự fallback nếu chưa cài)
    - Bản đồ phân bổ danh mục theo quốc gia (best-effort)
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import auth
import backtest as bt
import chatbot
import data_sources as ds
import portfolio_analytics as pa
import technical_indicators as ti
import ui_helpers as uih
import valuation as val

st.set_page_config(page_title="FinDash-VN", layout="wide", page_icon="📊")


# =============================================================================
# Helpers dùng chung
# =============================================================================
def pick_symbol(asset_class: str, key_prefix: str):
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
    """Widget chọn nhiều mã thuộc nhiều loại tài sản. Trả về list[(asset_class, symbol)]."""
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


ASSET_CODE_ALIASES = {
    "world": ds.ASSET_WORLD, "the gioi": ds.ASSET_WORLD, "thegioi": ds.ASSET_WORLD,
    "vn": ds.ASSET_VN, "viet nam": ds.ASSET_VN, "vietnam": ds.ASSET_VN,
    "crypto": ds.ASSET_CRYPTO, "tien dien tu": ds.ASSET_CRYPTO,
}


@st.dialog("🔍 Xem nhanh một mã khác")
def quick_lookup_dialog():
    ac = st.selectbox("Loại tài sản", ds.ASSET_CLASSES, key="dlg_ac")
    sym = pick_symbol(ac, "dlg")
    if st.button("Tra cứu", key="dlg_go"):
        info = ds.get_summary_info(ac, sym)
        if not info:
            st.warning("Không có dữ liệu.")
        else:
            st.table(pd.DataFrame(list(info.items())[:10], columns=["Chỉ tiêu", "Giá trị"]).set_index("Chỉ tiêu"))
        start, end = ds.period_to_dates("3 Tháng")
        hist = ds.get_price_history(ac, sym, start, end)
        if not hist.empty:
            st.plotly_chart(px.line(hist, x="Date", y="Close", title=f"{sym} — 3 tháng gần nhất"),
                             width="stretch")


# =============================================================================
# TRANG 1 — MỘT TÀI SẢN
# =============================================================================
def page_single_asset():
    st.title("📈 Một tài sản")
    st.sidebar.subheader("Chọn tài sản")
    asset_class = st.sidebar.selectbox("Loại tài sản", ds.ASSET_CLASSES, key="single_asset_class")
    symbol = pick_symbol(asset_class, "single")

    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button("🔍 Xem mã khác", width="stretch"):
            quick_lookup_dialog()
    with c2:
        live = st.toggle("🔴 Live", value=False, help="Tự động làm mới giá mỗi 30 giây")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Summary", "📈 Chart", "📊 Thống kê & Tài chính", "🔍 Phân tích",
        "🧪 Backtest", "💰 Định giá", "📰 Tin tức",
    ])

    with tab1:
        render_summary_tab(asset_class, symbol, live)
    with tab2:
        render_chart_tab(asset_class, symbol)
    with tab3:
        render_stats_financials_tab(asset_class, symbol)
    with tab4:
        render_analysis_tab(asset_class, symbol)
    with tab5:
        render_backtest_tab(asset_class, symbol)
    with tab6:
        render_valuation_tab(asset_class, symbol)
    with tab7:
        render_news_tab(asset_class, symbol)


@st.fragment(run_every="30s")
def _live_price_ticker(asset_class, symbol):
    info = ds.get_summary_info(asset_class, symbol)
    price = info.get("Previous Close") or info.get("Giá đóng cửa gần nhất")
    st.metric(f"Giá {symbol} (tự động làm mới 30s)", fmt(price) if price is not None else "—",
               help=f"Cập nhật lúc {datetime.now():%H:%M:%S}")


@st.fragment
def render_summary_tab(asset_class, symbol, live: bool):
    st.subheader(f"Summary — {symbol}")

    if live:
        _live_price_ticker(asset_class, symbol)

    with st.status("Đang tải dữ liệu Summary...", expanded=False) as status:
        info = ds.get_summary_info(asset_class, symbol)
        status.update(label="Đã tải xong", state="complete")

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
        uih.export_csv_button(
            pd.DataFrame(items, columns=["Chỉ tiêu", "Giá trị"]).set_index("Chỉ tiêu"),
            f"{symbol}_summary.csv", "⬇️ Tải Summary (CSV)", key=f"dl_summary_{symbol}",
        )

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
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("Không lấy được dữ liệu giá lịch sử.")


@st.fragment
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

    indicators = st.multiselect(
        "Chỉ báo kỹ thuật", ["Bollinger Bands", "RSI (14)", "MACD"], key="tech_indicators",
    )

    freq_map = {"Ngày": "D", "Tuần": "W", "Tháng": "ME"}
    with st.status("Đang tải dữ liệu giá...", expanded=False) as status:
        raw = ds.get_price_history(asset_class, symbol, start_date, end_date)
        status.update(label="Đã tải xong", state="complete")

    if raw.empty:
        st.warning("Không lấy được dữ liệu giá cho khoảng thời gian đã chọn.")
        return

    chart_df = ds.resample_ohlcv(raw, freq_map[sampling])
    chart_df["SMA20"] = chart_df["Close"].rolling(20).mean()

    extra_rows = sum(1 for x in ["RSI (14)", "MACD"] if x in indicators)
    n_rows = 1 + extra_rows
    if extra_rows == 0:
        row_heights = [1.0]
    else:
        row_heights = [0.55] + [0.45 / extra_rows] * extra_rows
    specs = [[{"secondary_y": True}]] + [[{"secondary_y": False}]] * extra_rows

    fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                         row_heights=row_heights, specs=specs)

    if plot_type == "Line":
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["Close"], mode="lines", name="Close"),
                       row=1, col=1, secondary_y=False)
    else:
        fig.add_trace(go.Candlestick(
            x=chart_df["Date"], open=chart_df["Open"], high=chart_df["High"],
            low=chart_df["Low"], close=chart_df["Close"], name="Candlestick",
        ), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["SMA20"], mode="lines", name="SMA 20"),
                   row=1, col=1, secondary_y=False)
    fig.add_trace(go.Bar(x=chart_df["Date"], y=chart_df["Volume"], name="Volume", opacity=0.3),
                   row=1, col=1, secondary_y=True)
    fig.update_yaxes(range=[0, chart_df["Volume"].max() * 4], showticklabels=False,
                      row=1, col=1, secondary_y=True)

    if "Bollinger Bands" in indicators:
        upper, mid, lower = ti.bollinger_bands(chart_df["Close"])
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=upper, mode="lines",
                                  line=dict(width=1, dash="dot"), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=lower, mode="lines",
                                  line=dict(width=1, dash="dot"), name="BB Lower",
                                  fill="tonexty", fillcolor="rgba(212,175,55,0.08)"), row=1, col=1)

    current_row = 2
    if "RSI (14)" in indicators:
        rsi_vals = ti.rsi(chart_df["Close"], 14)
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=rsi_vals, mode="lines", name="RSI(14)"),
                       row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
        current_row += 1

    if "MACD" in indicators:
        macd_line, signal_line, hist = ti.macd(chart_df["Close"])
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=macd_line, mode="lines", name="MACD"),
                       row=current_row, col=1)
        fig.add_trace(go.Scatter(x=chart_df["Date"], y=signal_line, mode="lines", name="Signal"),
                       row=current_row, col=1)
        fig.add_trace(go.Bar(x=chart_df["Date"], y=hist, name="Histogram", opacity=0.4),
                       row=current_row, col=1)
        fig.update_yaxes(title_text="MACD", row=current_row, col=1)
        current_row += 1

    fig.update_layout(title=f"{symbol} — Biến động giá & khối lượng ({sampling.lower()})",
                       height=550 + extra_rows * 200)
    st.plotly_chart(fig, width="stretch")

    uih.export_csv_button(chart_df.set_index("Date"), f"{symbol}_chart_data.csv",
                           "⬇️ Tải dữ liệu biểu đồ (CSV)", key=f"dl_chart_{symbol}")


@st.fragment
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

    with st.status("Đang tải báo cáo tài chính...", expanded=False) as status:
        data = ds.get_financials(asset_class, symbol, statement_key, period_key)
        status.update(label="Đã tải xong", state="complete")

    if data is None or data.empty:
        st.warning("Không có dữ liệu báo cáo tài chính cho lựa chọn này.")
    else:
        uih.show_table(data, key=f"fin_table_{symbol}_{statement_key}_{period_key}", height=400)
        uih.export_excel_button(
            {f"{statement_label}": data}, f"{symbol}_{statement_key}_{period_key}.xlsx",
            "⬇️ Tải báo cáo (Excel)", key=f"dl_fin_xlsx_{symbol}_{statement_key}",
        )


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
        uih.show_table(df, key=f"analysis_{symbol}_{name}", height=220)


@st.fragment
def render_backtest_tab(asset_class, symbol):
    st.subheader(f"Backtest chiến lược SMA Crossover — {symbol}")
    st.caption(
        "So sánh chiến lược 'giữ vị thế mua khi SMA nhanh > SMA chậm' với Mua & Giữ (Buy & Hold). "
        "Không tính phí giao dịch/trượt giá — chỉ mang tính minh hoạ học tập."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        fast = st.number_input("SMA nhanh (ngày)", 5, 100, 20, key="bt_fast")
    with c2:
        slow = st.number_input("SMA chậm (ngày)", 10, 300, 50, key="bt_slow")
    with c3:
        period_label = st.selectbox("Khoảng dữ liệu", list(ds.PERIOD_DAYS.keys()), index=4, key="bt_period")

    if fast >= slow:
        st.warning("SMA nhanh phải nhỏ hơn SMA chậm.")
        return

    start, end = ds.period_to_dates(period_label)
    with st.status("Đang tải dữ liệu & chạy backtest...", expanded=False) as status:
        hist = ds.get_price_history(asset_class, symbol, start, end)
        status.update(label="Đã tải xong", state="complete")

    if hist.empty or len(hist) < slow + 10:
        st.warning("Không đủ dữ liệu để backtest với khoảng thời gian/SMA đã chọn — thử khoảng thời gian dài hơn.")
        return

    res = bt.sma_crossover_backtest(hist, fast=int(fast), slow=int(slow))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res["df"]["Date"], y=res["df"]["strategy_equity"], name="Chiến lược SMA"))
    fig.add_trace(go.Scatter(x=res["df"]["Date"], y=res["df"]["buyhold_equity"], name="Mua & Giữ"))
    fig.update_layout(title="Giá trị danh mục theo thời gian (vốn ban đầu = 100)", height=450)
    st.plotly_chart(fig, width="stretch")

    st.dataframe(res["summary"].style.format("{:.2%}"), width="stretch")
    st.caption(f"Số lần đổi tín hiệu (ước lượng số giao dịch): {res['n_trades']}")

    uih.export_csv_button(res["df"].set_index("Date"), f"{symbol}_backtest.csv",
                           "⬇️ Tải dữ liệu backtest (CSV)", key=f"dl_bt_{symbol}")


@st.fragment
def render_valuation_tab(asset_class, symbol):
    st.subheader(f"Định giá nhanh — {symbol}")
    if asset_class == ds.ASSET_CRYPTO:
        st.info("Graham Number / DCF áp dụng cho cổ phiếu doanh nghiệp, không áp dụng cho tiền điện tử.")
        return
    st.caption(
        "Công cụ minh hoạ/học tập — số liệu tự động điền có thể thiếu hoặc không chính xác, "
        "nên kiểm tra lại trước khi dùng."
    )
    vinputs = ds.get_valuation_inputs(asset_class, symbol)

    st.markdown("#### 1. Graham Number")
    st.caption("Công thức Benjamin Graham: √(22.5 × EPS × BVPS) — ước tính giá hợp lý tối đa cho cổ phiếu giá trị.")
    c1, c2 = st.columns(2)
    with c1:
        eps = st.number_input("EPS (thu nhập/cổ phiếu)", value=float(vinputs["eps"] or 0.0), key="val_eps")
    with c2:
        bvps = st.number_input("BVPS (giá trị sổ sách/cổ phiếu)",
                                value=float(vinputs["book_value_per_share"] or 0.0), key="val_bvps")
    gn = val.graham_number(eps, bvps)
    if gn:
        st.metric("Graham Number", fmt(gn))
    else:
        st.info("Cần EPS và BVPS đều > 0 để tính Graham Number.")

    st.divider()
    st.markdown("#### 2. DCF (Discounted Cash Flow)")
    st.caption("Mô hình 2 giai đoạn: tăng trưởng đều trong N năm, sau đó tăng trưởng vĩnh viễn (Gordon Growth).")
    c1, c2, c3 = st.columns(3)
    with c1:
        fcf0 = st.number_input("FCF năm gần nhất", value=float(vinputs["fcf"] or 0.0), key="val_fcf")
        growth = st.number_input("Tăng trưởng FCF dự báo (%/năm)", 0.0, 50.0, 10.0, key="val_growth") / 100
    with c2:
        discount = st.number_input("Tỉ lệ chiết khấu / WACC (%/năm)", 1.0, 30.0, 12.0, key="val_discount") / 100
        terminal = st.number_input("Tăng trưởng vĩnh viễn (%/năm)", 0.0, 10.0, 3.0, key="val_terminal") / 100
    with c3:
        years = st.number_input("Số năm dự báo", 1, 15, 5, key="val_years")
        shares = st.number_input("Số CP lưu hành", value=float(vinputs["shares_outstanding"] or 0.0),
                                  key="val_shares")

    if fcf0 <= 0:
        st.info("Nhập FCF năm gần nhất > 0 để tính DCF.")
        return

    dcf_res = val.dcf_intrinsic_value(fcf0, growth, discount, terminal, int(years),
                                       shares if shares > 0 else None)
    if dcf_res is None:
        st.warning("Tỉ lệ chiết khấu phải lớn hơn tăng trưởng vĩnh viễn để mô hình hội tụ.")
        return

    c1, c2 = st.columns(2)
    c1.metric("Giá trị doanh nghiệp ước tính (Enterprise Value)", fmt(dcf_res["enterprise_value"]))
    if "value_per_share" in dcf_res:
        c2.metric("Giá trị ước tính / cổ phiếu", fmt(dcf_res["value_per_share"]))
    st.caption(
        "Kết quả DCF rất nhạy với giả định tăng trưởng/chiết khấu — chỉ mang tính tham khảo, "
        "không phải khuyến nghị đầu tư."
    )


def render_news_tab(asset_class, symbol):
    st.subheader(f"Tin tức gần đây — {symbol}")
    news = ds.get_news(asset_class, symbol, limit=8)
    if not news:
        st.info("Không lấy được tin tức cho mã này (nguồn có thể tạm thời không khả dụng).")
        return

    for item in news:
        title = item.get("title", "")
        link = item.get("link")
        publisher = item.get("publisher") or ""
        if link:
            st.markdown(f"- [{title}]({link}) — *{publisher}*")
        else:
            st.markdown(f"- {title} — *{publisher}*")

    st.divider()
    st.markdown("#### 🤖 Nhờ AI tóm tắt & đánh giá tác động")
    api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        st.info("Nhập Anthropic API Key ở trang Chatbot (sidebar) trước để dùng tính năng này.")
        return
    if st.button("Tóm tắt tin tức bằng AI", key=f"news_ai_{symbol}"):
        try:
            client = chatbot.get_client(api_key)
            with st.spinner("Đang phân tích..."):
                summary = chatbot.summarize_news(
                    client, symbol, [n["title"] for n in news],
                    model=st.session_state.get("anthropic_model", chatbot.DEFAULT_MODEL),
                )
            st.markdown(summary)
        except Exception as e:
            st.error(f"Lỗi khi gọi Claude API: {e}")


# =============================================================================
# TRANG 2 — DANH MỤC ĐẦU TƯ
# =============================================================================
def page_portfolio():
    st.title("💼 Danh mục đầu tư")
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
    base_currency = st.sidebar.radio(
        "Đơn vị tiền tệ chung danh mục", ["USD", "VND"], key="base_currency",
        help="Quy đổi tất cả tài sản về 1 đơn vị tiền tệ trước khi tính lợi suất danh mục — "
             "quan trọng khi trộn CP Việt Nam (VND) với CP thế giới/crypto (USD).",
    )

    with st.expander("📤 Nạp danh mục có sẵn từ file CSV (tuỳ chọn)"):
        st.caption("Cột cần có: `asset_class` (world/vn/crypto), `symbol`, `weight` (%).")
        up = st.file_uploader("Chọn file CSV", type=["csv"], key="portfolio_csv")
        if up is not None:
            try:
                up_df = pd.read_csv(up)
                up_df.columns = [c.strip().lower() for c in up_df.columns]
                world, vn, crypto, weights = [], [], [], {}
                for _, row in up_df.iterrows():
                    ac_raw = str(row["asset_class"]).strip().lower()
                    ac = ASSET_CODE_ALIASES.get(ac_raw, ac_raw)
                    sym = str(row["symbol"]).strip().upper()
                    w = float(row.get("weight", 0) or 0)
                    if ac == ds.ASSET_WORLD:
                        world.append(sym)
                    elif ac == ds.ASSET_VN:
                        vn.append(sym)
                    elif ac == ds.ASSET_CRYPTO:
                        crypto.append(sym)
                    else:
                        continue
                    weights[f"{ac}:{sym}"] = w
                st.session_state["port_world_multi"] = world
                st.session_state["port_vn_multi"] = vn
                st.session_state["port_crypto_multi"] = crypto
                st.session_state["uploaded_weights"] = weights
                st.success(f"Đã nạp {len(world) + len(vn) + len(crypto)} mã từ file. Đang làm mới trang...")
                st.rerun()
            except Exception as e:
                st.error(f"Không đọc được file: {e}")

    st.subheader("Chọn danh mục")
    picked = multi_pick_symbols("port")

    if len(picked) < 2:
        st.info("Chọn ít nhất 2 tài sản để phân tích danh mục.")
        return

    st.markdown("#### Tỉ trọng danh mục (có thể sửa trực tiếp trong bảng)")
    uploaded_w = st.session_state.get("uploaded_weights", {})
    equal_w = round(100 / len(picked), 2)
    weight_rows = [{
        "Loại tài sản": ac, "Mã": sym,
        "Tỉ trọng (%)": uploaded_w.get(f"{ac}:{sym}", equal_w),
    } for ac, sym in picked]
    weight_df = pd.DataFrame(weight_rows)

    try:
        edited = st.data_editor(
            weight_df, key="weight_editor", width="stretch", hide_index=True,
            disabled=["Loại tài sản", "Mã"],
            column_config={"Tỉ trọng (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.5)},
        )
    except Exception:
        edited = weight_df  # fallback nếu phiên bản Streamlit quá cũ không có data_editor

    total_w = edited["Tỉ trọng (%)"].sum()
    if total_w == 0:
        st.error("Tổng tỉ trọng phải > 0.")
        return
    st.caption(f"Tổng tỉ trọng nhập: {total_w:.1f}% → sẽ tự chuẩn hoá về 100% khi tính toán.")
    weights = {f"{r['Loại tài sản']}:{r['Mã']}": r["Tỉ trọng (%)"] for _, r in edited.iterrows()}

    with st.status("Đang tải giá & tính toán danh mục...", expanded=True) as status:
        st.write(f"Đang tải tỉ giá USD/VND...")
        fx_hist = ds.get_fx_history(start, end)

        returns_dict = {}
        for ac, sym in picked:
            st.write(f"Đang tải {sym} ({ac})...")
            hist = ds.get_price_history(ac, sym, start, end)
            if hist.empty or len(hist) < 30:
                st.write(f"⚠️ Bỏ qua {sym}: không đủ dữ liệu.")
                continue
            native_ccy = ds.ASSET_CURRENCY[ac]
            if native_ccy != base_currency:
                if fx_hist.empty:
                    st.write(f"⚠️ Không lấy được tỉ giá — {sym} vẫn tính theo {native_ccy} gốc.")
                else:
                    hist = ds.convert_price_series(hist, native_ccy, base_currency, fx_hist)
            returns_dict[f"{ac}:{sym}"] = pa.prices_to_returns(hist)

        if len(returns_dict) < 2:
            status.update(label="Không đủ dữ liệu", state="error")
            st.error("Không đủ dữ liệu để phân tích danh mục. Hãy chọn khoảng thời gian dài hơn.")
            return

        returns_df = pa.align_returns(returns_dict)
        valid_keys = list(returns_df.columns)
        norm_weights = np.array([weights[k] for k in valid_keys])
        norm_weights = norm_weights / norm_weights.sum()

        st.write("Đang tải chỉ số benchmark...")
        bench_hist = ds.get_benchmark_history(benchmark_class, start, end)
        bench_returns = pa.prices_to_returns(bench_hist) if not bench_hist.empty else pd.Series(dtype=float)
        status.update(label="Hoàn tất", state="complete")

    tab_capm, tab_apt, tab_stats, tab_opt, tab_mc, tab_map = st.tabs([
        "📐 CAPM", "🧮 APT", "📊 Thống kê danh mục", "🎯 Tối ưu hoá",
        "🎲 Monte Carlo Simulation", "🗺️ Phân bổ địa lý",
    ])

    with tab_capm:
        render_capm_tab(returns_df, bench_returns, rf_annual, benchmark_class)
    with tab_apt:
        render_apt_tab(returns_df, benchmark_class, start, end, rf_annual)
    with tab_stats:
        port_stats = render_portfolio_stats_tab(returns_df, norm_weights, rf_annual, valid_keys, base_currency)
        st.session_state["last_portfolio_stats"] = port_stats
        st.session_state["last_portfolio_tickers"] = valid_keys
    with tab_opt:
        render_optimization_tab(returns_df, rf_annual, norm_weights, valid_keys)
    with tab_mc:
        render_monte_carlo_tab(returns_df, norm_weights, valid_keys)
    with tab_map:
        render_geo_tab(picked)

    st.divider()
    render_portfolio_export(returns_df, bench_returns, rf_annual, benchmark_class,
                             norm_weights, valid_keys)


@st.fragment
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
        width="stretch",
    )
    st.session_state["last_capm_df"] = res_df

    fig = px.bar(res_df.reset_index(), x="Tài sản", y="Beta", title="Beta của từng tài sản so với benchmark")
    fig.add_hline(y=1, line_dash="dash", annotation_text="Beta thị trường = 1")
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Đường thị trường chứng khoán (SML): E[R] = Rf + β × (E[Rm] − Rf). "
        "Beta > 1: biến động mạnh hơn thị trường; Beta < 1: biến động nhẹ hơn."
    )


@st.fragment
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
        bh = ds.get_benchmark_history(ds.ASSET_VN, start, end) if tk is None else \
            ds.get_price_history(ds.ASSET_WORLD, tk, start, end)
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
    betas_df = pd.DataFrame(betas_table).T
    st.dataframe(betas_df.style.format("{:.3f}"), width="stretch")

    st.markdown("**Kết quả hồi quy APT**")
    res_df = pd.DataFrame(rows).set_index("Tài sản")
    st.dataframe(
        res_df.style.format({"Alpha (năm)": "{:.2%}", "R²": "{:.2f}", "E[R] APT (năm)": "{:.2%}"}),
        width="stretch",
    )
    st.session_state["last_apt_df"] = res_df
    st.session_state["last_apt_betas_df"] = betas_df
    st.caption(
        "APT giả định lợi suất tài sản chịu ảnh hưởng bởi nhiều nhân tố rủi ro hệ thống "
        "(thay vì chỉ thị trường như CAPM). Đây là bản đơn giản hoá phục vụ mục đích học tập."
    )


def render_portfolio_stats_tab(returns_df, weights, rf_annual, keys, base_currency):
    stats = pa.portfolio_stats(returns_df, weights, rf_annual)
    ext = pa.extended_risk_metrics(returns_df, weights, rf_annual)

    st.caption(f"Toàn bộ tài sản đã được quy đổi về đơn vị tiền tệ chung: **{base_currency}**.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Lợi suất kỳ vọng (năm)", f"{stats['expected_return_annual']:.2%}")
    c2.metric("Độ biến động (năm)", f"{stats['volatility_annual']:.2%}")
    c3.metric("Sharpe Ratio", f"{stats['sharpe_ratio']:.2f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Max Drawdown", f"{ext['max_drawdown']:.2%}")
    c5.metric("Sortino Ratio", f"{ext['sortino_ratio']:.2f}")
    c6.metric("Calmar Ratio", f"{ext['calmar_ratio']:.2f}")
    st.caption(
        "Sortino: giống Sharpe nhưng chỉ phạt biến động giảm giá (downside). "
        "Calmar: lợi suất năm hoá so với mức sụt giảm tối đa (Max Drawdown) — càng cao càng tốt."
    )

    st.markdown("**Đường giá trị danh mục & Drawdown**")
    fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                            row_heights=[0.65, 0.35])
    fig_eq.add_trace(go.Scatter(x=ext["equity_curve"].index, y=ext["equity_curve"].values,
                                 mode="lines", name="Giá trị danh mục"), row=1, col=1)
    fig_eq.add_trace(go.Scatter(x=ext["drawdown_series"].index, y=ext["drawdown_series"].values,
                                 mode="lines", fill="tozeroy", name="Drawdown",
                                 line=dict(color="red")), row=2, col=1)
    fig_eq.update_yaxes(title_text="Giá trị (mua & giữ, vốn=100)", row=1, col=1)
    fig_eq.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
    fig_eq.update_layout(height=500, title="Giá trị danh mục theo thời gian & mức sụt giảm từ đỉnh")
    st.plotly_chart(fig_eq, width="stretch")

    st.markdown("**Ma trận tương quan**")
    fig = px.imshow(stats["corr_matrix"], text_auto=".2f", color_continuous_scale="RdBu_r",
                     zmin=-1, zmax=1, title="Tương quan lợi suất giữa các tài sản")
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Tỉ trọng danh mục**")
    w_df = pd.DataFrame({"Tài sản": keys, "Tỉ trọng": weights})
    st.plotly_chart(px.pie(w_df, names="Tài sản", values="Tỉ trọng", title="Phân bổ danh mục"),
                     width="stretch")

    stats["max_drawdown"] = ext["max_drawdown"]
    stats["sortino_ratio"] = ext["sortino_ratio"]
    stats["calmar_ratio"] = ext["calmar_ratio"]
    return stats


@st.fragment
def render_optimization_tab(returns_df, rf_annual, current_weights, keys):
    st.markdown("Tối ưu hoá danh mục theo mô hình Markowitz (không bán khống — tỉ trọng ≥ 0).")

    minvar = pa.optimize_min_variance(returns_df)
    maxsharpe = pa.optimize_max_sharpe(returns_df, rf_annual)
    frontier = pa.efficient_frontier_curve(returns_df, n_points=25)
    cloud = pa.random_portfolios(returns_df, n=1500, rf_annual=rf_annual, seed=42)

    cur_ret = float(current_weights @ (returns_df.mean().values * pa.TRADING_DAYS))
    cur_cov = returns_df.cov().values * pa.TRADING_DAYS
    cur_vol = float(np.sqrt(current_weights @ cur_cov @ current_weights))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cloud["volatility"], y=cloud["return"], mode="markers",
        marker=dict(size=4, color=cloud["sharpe"], colorscale="Viridis", showscale=True,
                    colorbar=dict(title="Sharpe")),
        name="Danh mục ngẫu nhiên", opacity=0.5,
    ))
    if not frontier.empty:
        fig.add_trace(go.Scatter(x=frontier["volatility"], y=frontier["target_return"], mode="lines",
                                  line=dict(color="white", width=3), name="Đường biên hiệu quả"))
    fig.add_trace(go.Scatter(
        x=[minvar["volatility_annual"]], y=[minvar["expected_return_annual"]], mode="markers",
        marker=dict(size=15, symbol="star", color="cyan"), name="Min Variance",
    ))
    fig.add_trace(go.Scatter(
        x=[maxsharpe["volatility_annual"]], y=[maxsharpe["expected_return_annual"]], mode="markers",
        marker=dict(size=15, symbol="star", color="gold"), name="Max Sharpe",
    ))
    fig.add_trace(go.Scatter(
        x=[cur_vol], y=[cur_ret], mode="markers",
        marker=dict(size=15, symbol="diamond", color="red"), name="Danh mục hiện tại của bạn",
    ))
    fig.update_layout(
        title="Efficient Frontier — Độ biến động (rủi ro) vs Lợi suất kỳ vọng",
        xaxis_title="Độ biến động (năm)", yaxis_title="Lợi suất kỳ vọng (năm)", height=550,
    )
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🔵 Danh mục Min Variance** (rủi ro thấp nhất)")
        mv_df = pd.DataFrame(list(minvar["weights"].items()), columns=["Tài sản", "Tỉ trọng"]).set_index("Tài sản")
        st.dataframe(mv_df.style.format("{:.1%}"), width="stretch")
        st.caption(f"E[R] = {minvar['expected_return_annual']:.2%} · Độ biến động = {minvar['volatility_annual']:.2%}")
        if st.button("✅ Áp dụng tỉ trọng này", key="apply_minvar"):
            _apply_optimal_weights(minvar["weights"])
    with c2:
        st.markdown("**🟡 Danh mục Max Sharpe** (hiệu quả rủi ro/lợi nhuận tốt nhất)")
        ms_df = pd.DataFrame(list(maxsharpe["weights"].items()), columns=["Tài sản", "Tỉ trọng"]).set_index("Tài sản")
        st.dataframe(ms_df.style.format("{:.1%}"), width="stretch")
        st.caption(
            f"E[R] = {maxsharpe['expected_return_annual']:.2%} · "
            f"Độ biến động = {maxsharpe['volatility_annual']:.2%} · Sharpe = {maxsharpe['sharpe_ratio']:.2f}"
        )
        if st.button("✅ Áp dụng tỉ trọng này", key="apply_maxsharpe"):
            _apply_optimal_weights(maxsharpe["weights"])

    st.caption(
        "Đường biên hiệu quả (efficient frontier) là tập hợp các danh mục có độ biến động thấp nhất "
        "cho mỗi mức lợi suất kỳ vọng. Nhấn nút 'Áp dụng' để tự động điền tỉ trọng tối ưu vào bảng "
        "chỉnh tỉ trọng ở đầu trang (tab 📊 Thống kê danh mục sẽ cập nhật theo tỉ trọng mới sau khi áp dụng)."
    )


def _apply_optimal_weights(weights_dict: dict):
    """Ghi tỉ trọng tối ưu vào session_state rồi rerun để bảng data_editor nạp lại giá trị mới."""
    st.session_state["uploaded_weights"] = {k: v * 100 for k, v in weights_dict.items()}
    if "weight_editor" in st.session_state:
        del st.session_state["weight_editor"]
    st.rerun()


@st.fragment
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
    st.plotly_chart(fig, width="stretch")

    var_res = pa.value_at_risk(ending_values, initial_value, confidence)
    hist_fig = px.histogram(ending_values, nbins=50, title="Phân phối giá trị danh mục cuối kỳ")
    hist_fig.add_vline(x=var_res["threshold_value"], line_dash="dash", line_color="red",
                        annotation_text=f"Ngưỡng {int((1 - confidence) * 100)}th percentile")
    st.plotly_chart(hist_fig, width="stretch")

    c1, c2 = st.columns(2)
    c1.metric(f"Value at Risk (VaR) @ {int(confidence * 100)}%", f"{var_res['VaR']:.2f}")
    c2.metric(f"Conditional VaR (CVaR) @ {int(confidence * 100)}%", f"{var_res['CVaR']:.2f}")
    st.caption(
        "VaR: khoản lỗ tối đa kỳ vọng ở mức tin cậy đã chọn. "
        "CVaR (Expected Shortfall): mức lỗ trung bình trong các kịch bản tệ hơn VaR."
    )
    st.session_state["last_mc_summary"] = pd.DataFrame([{
        "Số lượt mô phỏng": n_sims, "Số ngày": horizon, "Độ tin cậy": confidence,
        "VaR": var_res["VaR"], "CVaR": var_res["CVaR"],
    }])


def render_geo_tab(picked):
    st.caption("Phân bổ danh mục theo quốc gia/thị trường (best-effort — một số mã có thể thiếu thông tin).")
    rows = []
    for ac, sym in picked:
        country = ds.get_country_info(ac, sym)
        rows.append({"Mã": sym, "Loại tài sản": ac, "Quốc gia": country or "Không xác định"})
    geo_df = pd.DataFrame(rows)
    counts = geo_df.groupby("Quốc gia").size().reset_index(name="Số mã")

    try:
        fig = px.scatter_geo(
            counts[counts["Quốc gia"] != "Không xác định"],
            locations="Quốc gia", locationmode="country names", size="Số mã",
            projection="natural earth", title="Phân bổ danh mục theo quốc gia",
        )
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.info("Không vẽ được bản đồ — hiển thị dạng bảng bên dưới.")
    st.dataframe(counts, width="stretch")


def render_portfolio_export(returns_df, bench_returns, rf_annual, benchmark_class, weights, keys):
    st.markdown("#### 📤 Xuất báo cáo danh mục")
    stats = pa.portfolio_stats(returns_df, weights, rf_annual)
    capm_df = st.session_state.get("last_capm_df", pd.DataFrame())
    apt_df = st.session_state.get("last_apt_df", pd.DataFrame())
    mc_df = st.session_state.get("last_mc_summary", pd.DataFrame())

    summary_df = pd.DataFrame([{
        "Danh mục": ", ".join(keys),
        "Lợi suất kỳ vọng (năm)": stats["expected_return_annual"],
        "Độ biến động (năm)": stats["volatility_annual"],
        "Sharpe Ratio": stats["sharpe_ratio"],
        "Benchmark": benchmark_class,
        "Rf (%/năm)": rf_annual * 100,
    }])

    c1, c2, c3 = st.columns(3)
    with c1:
        uih.export_csv_button(summary_df.set_index("Danh mục"), "portfolio_summary.csv",
                               "⬇️ CSV", key="dl_port_csv")
    with c2:
        uih.export_excel_button(
            {"Tổng quan": summary_df, "CAPM": capm_df, "APT": apt_df, "Monte Carlo": mc_df,
             "Tương quan": stats["corr_matrix"]},
            "portfolio_report.xlsx", "⬇️ Excel", key="dl_port_xlsx",
        )
    with c3:
        sections = [
            ("Tổng quan danh mục", summary_df),
            ("CAPM", capm_df),
            ("APT", apt_df),
            ("Monte Carlo Simulation", mc_df),
        ]
        uih.export_pdf_button("FinDash-VN — Báo cáo Danh mục Đầu tư", sections,
                               "portfolio_report.pdf", "⬇️ PDF", key="dl_port_pdf")


# =============================================================================
# TRANG 3 — CHATBOT
# =============================================================================
def page_chatbot():
    st.title("💬 Chatbot hỗ trợ đầu tư")
    st.caption("Dùng Anthropic Claude API. Nhập API key ở sidebar (chỉ lưu trong phiên làm việc).")

    try:
        default_key = st.secrets.get("anthropic", {}).get("api_key", "")
    except Exception:
        default_key = ""  # chưa có file .streamlit/secrets.toml — bình thường, không phải lỗi
    api_key = st.sidebar.text_input("Anthropic API Key", type="password",
                                     value=default_key, key="anthropic_api_key")
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
# MAIN — theme/logo, auth gate, multipage navigation
# =============================================================================
def main():
    try:
        st.logo("assets/logo.png", icon_image="assets/icon.png")
    except Exception:
        pass

    if not auth.require_login():
        return  # auth.require_login() đã tự vẽ màn hình đăng nhập + st.stop()

    single = st.Page(page_single_asset, title="Một tài sản", icon="📈", url_path="single-asset", default=True)
    portfolio = st.Page(page_portfolio, title="Danh mục đầu tư", icon="💼", url_path="portfolio")
    bot = st.Page(page_chatbot, title="Chatbot", icon="💬", url_path="chatbot")

    nav = st.navigation([single, portfolio, bot])
    nav.run()


if __name__ == "__main__":
    main()
