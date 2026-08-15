"""
data_sources.py
================
Lớp truy xuất dữ liệu hợp nhất (unified data layer) cho FinDash-VN.
Hỗ trợ 3 nhóm tài sản:
    - World Stock : lấy qua yfinance (Yahoo Finance)
    - VN Stock    : lấy qua vnstock v4 (nguồn VCI/KBS)
    - Crypto      : lấy qua yfinance (mã dạng "BTC-USD")

Mọi hàm lấy dữ liệu đều được @st.cache_data để tránh gọi API quá nhiều lần
(vnstock ở chế độ khách giới hạn ~20 request/phút).
"""
import io
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

ASSET_WORLD = "Cổ phiếu Thế giới"
ASSET_VN = "Cổ phiếu Việt Nam"
ASSET_CRYPTO = "Tiền điện tử"

ASSET_CLASSES = [ASSET_WORLD, ASSET_VN, ASSET_CRYPTO]

# Đơn vị tiền tệ gốc của mỗi loại tài sản — dùng cho quy đổi ngoại tệ khi gộp danh mục
ASSET_CURRENCY = {ASSET_WORLD: "USD", ASSET_VN: "VND", ASSET_CRYPTO: "USD"}

# ---------------------------------------------------------------------------
# Danh sách mã tiêu biểu — dùng làm lựa chọn nhanh và fallback khi không lấy
# được danh sách đầy đủ từ nguồn động (Wikipedia / vnstock Listing).
# ---------------------------------------------------------------------------
WORLD_STOCK_SHORTLIST = sorted([
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM",
    "V", "UNH", "XOM", "JNJ", "WMT", "PG", "MA", "HD", "CVX", "KO", "PEP",
    "BAC", "DIS", "NFLX", "ADBE", "CRM", "INTC", "AMD", "PFE", "T", "VZ",
])

VN_STOCK_SHORTLIST = sorted([
    "VNM", "VCB", "VIC", "VHM", "HPG", "FPT", "MSN", "MWG", "GAS", "CTG",
    "BID", "TCB", "ACB", "MBB", "VPB", "SSI", "STB", "POW", "PLX", "SAB",
    "VJC", "VRE", "PNJ", "REE", "GVR", "DGC", "KDH", "NVL", "DXG", "HDB",
])

CRYPTO_SHORTLIST = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "BNB-USD": "BNB",
    "SOL-USD": "Solana", "XRP-USD": "XRP", "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin", "AVAX-USD": "Avalanche", "DOT-USD": "Polkadot",
    "MATIC-USD": "Polygon", "LINK-USD": "Chainlink", "LTC-USD": "Litecoin",
}

# Top 10 theo vốn hoá ước lượng (thứ tự cố định, KHÔNG alphabet hoá) — dùng cho
# bảng giá real-time ở Trang chủ, khác với shortlist chọn nhanh ở trên.
WORLD_TOP10 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "TSLA", "JPM", "V"]
VN_TOP10 = ["VCB", "VIC", "VHM", "HPG", "FPT", "GAS", "MSN", "CTG", "BID", "VNM"]
CRYPTO_TOP10 = list(CRYPTO_SHORTLIST.keys())[:10]

PERIOD_DAYS = {
    "1 Tháng": 30, "3 Tháng": 91, "6 Tháng": 182, "1 Năm": 365,
    "3 Năm": 365 * 3, "5 Năm": 365 * 5, "Tối đa": 365 * 15,
}


def period_to_dates(period_label: str):
    """Chuyển nhãn khoảng thời gian (vd '1 Năm') thành (start_date, end_date)."""
    end = datetime.today().date()
    if period_label == "YTD":
        start = datetime(end.year, 1, 1).date()
    else:
        days = PERIOD_DAYS.get(period_label, 365)
        start = end - timedelta(days=days)
    return start, end


# ---------------------------------------------------------------------------
# Danh sách mã (dropdown)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_world_stock_list():
    """Danh sách mã S&P 500, scrape từ Wikipedia; fallback về shortlist nếu lỗi."""
    try:
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=8,
        )
        tables = pd.read_html(io.StringIO(resp.text))
        tickers = sorted(tables[0]["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist())
        return tickers if tickers else WORLD_STOCK_SHORTLIST
    except Exception:
        return WORLD_STOCK_SHORTLIST


@st.cache_data(ttl=3600, show_spinner=False)
def get_vn_stock_list():
    """Danh sách mã CP sàn HOSE/HNX/UPCOM qua vnstock; fallback về shortlist nếu lỗi."""
    try:
        from vnstock import Listing
        df = Listing(source="KBS").all_symbols()
        col = "symbol" if "symbol" in df.columns else df.columns[0]
        tickers = sorted(df[col].dropna().astype(str).unique().tolist())
        return tickers if tickers else VN_STOCK_SHORTLIST
    except Exception:
        return VN_STOCK_SHORTLIST


def get_crypto_list():
    return CRYPTO_SHORTLIST


# ---------------------------------------------------------------------------
# Giá lịch sử (OHLCV) — luôn trả về DataFrame chuẩn hoá cột:
# Date, Open, High, Low, Close, Volume
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def get_price_history(asset_class: str, symbol: str, start, end) -> pd.DataFrame:
    start, end = str(start), str(end)

    if asset_class in (ASSET_WORLD, ASSET_CRYPTO):
        df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns={"Datetime": "Date"})
        return df[["Date", "Open", "High", "Low", "Close", "Volume"]]

    elif asset_class == ASSET_VN:
        try:
            from vnstock import Quote
            q = Quote(symbol=symbol, source="VCI")
            df = q.history(start=start, end=end, interval="1D")
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.rename(columns={
                "time": "Date", "open": "Open", "high": "High",
                "low": "Low", "close": "Close", "volume": "Volume",
            })
            df["Date"] = pd.to_datetime(df["Date"])
            return df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            st.warning(f"Không lấy được dữ liệu giá cho {symbol}: {e}")
            return pd.DataFrame()

    return pd.DataFrame()


def resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """freq: 'D' (ngày) | 'W' (tuần) | 'ME' (tháng)"""
    if df.empty:
        return df
    d = df.set_index("Date")
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    out = d.resample(freq).agg(agg).dropna(how="all").reset_index()
    return out


# ---------------------------------------------------------------------------
# Thông tin tóm tắt (tab Summary)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def get_summary_info(asset_class: str, symbol: str) -> dict:
    info = {}
    if asset_class in (ASSET_WORLD, ASSET_CRYPTO):
        try:
            raw = yf.Ticker(symbol).info or {}
            fields = [
                ("previousClose", "Previous Close"), ("open", "Open"),
                ("dayLow", "Day Low"), ("dayHigh", "Day High"),
                ("fiftyTwoWeekLow", "52 Week Low"), ("fiftyTwoWeekHigh", "52 Week High"),
                ("volume", "Volume"), ("averageVolume", "Avg. Volume"),
                ("marketCap", "Market Cap"), ("beta", "Beta (5Y Monthly)"),
                ("trailingPE", "PE Ratio (TTM)"), ("trailingEps", "EPS (TTM)"),
                ("dividendYield", "Dividend Yield"), ("targetMeanPrice", "1y Target Est"),
            ]
            for key, label in fields:
                if raw.get(key) is not None:
                    info[label] = raw[key]
        except Exception as e:
            st.warning(f"Không lấy được summary cho {symbol}: {e}")

    elif asset_class == ASSET_VN:
        try:
            from vnstock import Company
            overview = Company(symbol=symbol, source="VCI").overview()
            if overview is not None and not overview.empty:
                row = overview.iloc[0].to_dict()
                for k, v in row.items():
                    if v is not None and str(v) != "":
                        info[k] = v
            hist = get_price_history(
                asset_class, symbol,
                datetime.today().date() - timedelta(days=10), datetime.today().date(),
            )
            if not hist.empty:
                info["Giá đóng cửa gần nhất"] = hist.iloc[-1]["Close"]
                info["Khối lượng gần nhất"] = hist.iloc[-1]["Volume"]
        except Exception as e:
            st.warning(f"Không lấy được summary cho {symbol}: {e}")

    return info


# ---------------------------------------------------------------------------
# Báo cáo tài chính (chỉ áp dụng cho cổ phiếu — World & VN, không áp dụng crypto)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_financials(asset_class: str, symbol: str, statement: str, period: str) -> pd.DataFrame:
    """statement: 'income' | 'balance' | 'cashflow' ; period: 'year' | 'quarter'"""
    if asset_class == ASSET_WORLD:
        try:
            t = yf.Ticker(symbol)
            table = {
                ("income", "year"): t.financials,
                ("income", "quarter"): t.quarterly_financials,
                ("balance", "year"): t.balance_sheet,
                ("balance", "quarter"): t.quarterly_balance_sheet,
                ("cashflow", "year"): t.cashflow,
                ("cashflow", "quarter"): t.quarterly_cashflow,
            }
            return table.get((statement, period), pd.DataFrame())
        except Exception as e:
            st.warning(f"Không lấy được báo cáo tài chính cho {symbol}: {e}")
            return pd.DataFrame()

    elif asset_class == ASSET_VN:
        try:
            from vnstock import Finance
            f = Finance(symbol=symbol, source="VCI")
            fn = {"income": f.income_statement, "balance": f.balance_sheet, "cashflow": f.cash_flow}[statement]
            return fn(period=period)
        except Exception as e:
            st.warning(f"Không lấy được báo cáo tài chính cho {symbol}: {e}")
            return pd.DataFrame()

    return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def get_analyst_estimates(symbol: str) -> dict:
    """Ước tính từ giới phân tích — chỉ scrape đáng tin cậy cho cổ phiếu thế giới."""
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}/analysis"
        headers = {"User-Agent": "Mozilla/5.0"}
        tables = pd.read_html(io.StringIO(requests.get(url, headers=headers, timeout=8).text))
        names = ["Earnings Estimate", "Revenue Estimate", "Earnings History",
                 "EPS Trend", "EPS Revisions", "Growth Estimates"]
        return {name: tables[i] for i, name in enumerate(names) if i < len(tables)}
    except Exception as e:
        st.info(f"Không lấy được dữ liệu phân tích cho {symbol}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Chỉ số tham chiếu (benchmark) dùng cho CAPM
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_country_info(asset_class: str, symbol: str) -> str:
    """Quốc gia trụ sở/thị trường chính — dùng cho bản đồ phân bổ danh mục.
    Cố gắng lấy tốt nhất có thể; trả về None nếu không xác định được."""
    if asset_class == ASSET_VN:
        return "Vietnam"
    if asset_class == ASSET_CRYPTO:
        return None  # crypto không gắn với 1 quốc gia cụ thể
    try:
        raw = yf.Ticker(symbol).info or {}
        return raw.get("country")
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def get_benchmark_history(asset_class: str, start, end) -> pd.DataFrame:
    """S&P500 (^GSPC) cho World/Crypto; VNINDEX cho VN Stock."""
    if asset_class == ASSET_VN:
        try:
            from vnstock import Quote
            q = Quote(symbol="VNINDEX", source="VCI")
            df = q.history(start=str(start), end=str(end), interval="1D")
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.rename(columns={"time": "Date", "close": "Close"})
            df["Date"] = pd.to_datetime(df["Date"])
            return df[["Date", "Close"]]
        except Exception:
            return pd.DataFrame()
    else:
        df = yf.download("^GSPC", start=str(start), end=str(end), interval="1d", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df[["Date", "Close"]]


# ---------------------------------------------------------------------------
# Tỉ giá & quy đổi ngoại tệ (dùng khi gộp danh mục nhiều loại tiền tệ)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_fx_history(start, end) -> pd.DataFrame:
    """Tỉ giá USD/VND (số VND đổi được 1 USD) theo ngày — cột Date, Rate."""
    try:
        df = yf.download("VND=X", start=str(start), end=str(end), interval="1d", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns={"Close": "Rate"})
        return df[["Date", "Rate"]]
    except Exception:
        return pd.DataFrame()


def convert_price_series(price_df: pd.DataFrame, from_ccy: str, to_ccy: str,
                          fx_history: pd.DataFrame) -> pd.DataFrame:
    """Quy đổi các cột giá (Open/High/Low/Close) từ from_ccy sang to_ccy.
    fx_history: cột Date, Rate = số VND / 1 USD. Không đổi gì nếu from_ccy == to_ccy."""
    if from_ccy == to_ccy or price_df.empty or fx_history.empty:
        return price_df
    merged = price_df.merge(fx_history, on="Date", how="left")
    merged["Rate"] = merged["Rate"].ffill().bfill()
    price_cols = [c for c in ["Open", "High", "Low", "Close"] if c in merged.columns]
    if from_ccy == "VND" and to_ccy == "USD":
        for c in price_cols:
            merged[c] = merged[c] / merged["Rate"]
    elif from_ccy == "USD" and to_ccy == "VND":
        for c in price_cols:
            merged[c] = merged[c] * merged["Rate"]
    return merged.drop(columns=["Rate"])


# ---------------------------------------------------------------------------
# Dữ liệu phục vụ định giá (Graham Number / DCF) — best-effort
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_valuation_inputs(asset_class: str, symbol: str) -> dict:
    """Cố gắng lấy EPS, giá trị sổ sách/CP, số CP lưu hành, FCF gần nhất.
    Luôn nên cho người dùng xem lại/sửa tay các số này trước khi tính toán."""
    result = {"eps": None, "book_value_per_share": None, "shares_outstanding": None, "fcf": None}

    if asset_class == ASSET_WORLD:
        try:
            t = yf.Ticker(symbol)
            raw = t.info or {}
            result["eps"] = raw.get("trailingEps")
            result["book_value_per_share"] = raw.get("bookValue")
            result["shares_outstanding"] = raw.get("sharesOutstanding")
            cf = t.cashflow
            if cf is not None and not cf.empty:
                for row_name in ["Free Cash Flow", "FreeCashFlow"]:
                    if row_name in cf.index:
                        result["fcf"] = float(cf.loc[row_name].iloc[0])
                        break
        except Exception:
            pass

    elif asset_class == ASSET_VN:
        try:
            from vnstock import Finance
            ratio = Finance(symbol=symbol, source="VCI").ratio(period="year")
            if ratio is not None and not ratio.empty:
                row = ratio.iloc[0]
                for col in ratio.columns:
                    lc = str(col).lower()
                    if "eps" in lc and result["eps"] is None:
                        result["eps"] = row[col]
                    if ("bvps" in lc or "book" in lc) and result["book_value_per_share"] is None:
                        result["book_value_per_share"] = row[col]
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Tin tức gần đây (chỉ lấy tiêu đề + link, không lấy nội dung đầy đủ)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def get_news(asset_class: str, symbol: str, limit: int = 8) -> list:
    """Trả về list[dict]: [{'title':.., 'link':.., 'publisher':..}, ...] (best-effort,
    cấu trúc response của Yahoo/vnstock có thể thay đổi theo thời gian)."""
    items = []

    if asset_class in (ASSET_WORLD, ASSET_CRYPTO):
        try:
            raw_news = yf.Ticker(symbol).get_news(count=limit) or []
            for a in raw_news:
                content = a.get("content", a) if isinstance(a, dict) else {}
                title = content.get("title") or a.get("title")
                link = (
                    (content.get("canonicalUrl") or {}).get("url")
                    or (content.get("clickThroughUrl") or {}).get("url")
                    or a.get("link")
                )
                publisher = (content.get("provider") or {}).get("displayName") or a.get("publisher")
                if title:
                    items.append({"title": title, "link": link, "publisher": publisher})
        except Exception:
            pass

    elif asset_class == ASSET_VN:
        try:
            from vnstock import Company
            news_df = Company(symbol=symbol, source="VCI").news()
            if news_df is not None and not news_df.empty:
                cols = list(news_df.columns)
                title_col = next((c for c in cols if "title" in c.lower() or "headline" in c.lower()), cols[0])
                link_col = next((c for c in cols if "link" in c.lower() or "url" in c.lower()), None)
                for _, row in news_df.head(limit).iterrows():
                    items.append({
                        "title": str(row[title_col]),
                        "link": str(row[link_col]) if link_col else None,
                        "publisher": "vnstock",
                    })
        except Exception:
            pass

    return items[:limit]


# ---------------------------------------------------------------------------
# Bảng giá gần-thời-gian-thực (dùng cho Trang chủ — Top 10 mỗi nhóm tài sản)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=25, show_spinner=False)
def get_realtime_board(asset_class: str, symbols: list) -> pd.DataFrame:
    """Trả về DataFrame cột: Mã, Giá, % Thay đổi (so với phiên trước)."""
    rows = []

    if asset_class in (ASSET_WORLD, ASSET_CRYPTO):
        try:
            data = yf.download(symbols, period="5d", interval="1d", progress=False, group_by="ticker")
            multi = isinstance(data.columns, pd.MultiIndex)
            for sym in symbols:
                try:
                    sdf = data[sym] if multi else data
                    closes = sdf["Close"].dropna()
                    if len(closes) >= 2:
                        last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
                        chg = (last / prev - 1) if prev else None
                    elif len(closes) == 1:
                        last, chg = float(closes.iloc[-1]), None
                    else:
                        last, chg = None, None
                    rows.append({"Mã": sym, "Giá": last, "% Thay đổi": chg})
                except Exception:
                    rows.append({"Mã": sym, "Giá": None, "% Thay đổi": None})
        except Exception:
            rows = [{"Mã": s, "Giá": None, "% Thay đổi": None} for s in symbols]

    elif asset_class == ASSET_VN:
        # Ưu tiên price_board (1 lần gọi cho cả danh sách) — nhanh hơn nhiều và đỡ tốn
        # hạn mức request so với gọi lặp từng mã. Giới hạn thời gian chờ cứng (12s) vì
        # vnstock tự retry/backoff nội bộ khá lâu khi API đang bị giới hạn — không để nó
        # kéo dài làm treo cả trang.
        try:
            import concurrent.futures
            from vnstock import Trading

            def _fetch_board():
                return Trading(source="VCI").price_board(symbols)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                board = ex.submit(_fetch_board).result(timeout=12)

            if board is not None and not board.empty:
                cols = [str(c).lower() for c in board.columns]

                def _find_col(*keywords):
                    for i, c in enumerate(cols):
                        if any(k in c for k in keywords):
                            return board.columns[i]
                    return None

                sym_col = _find_col("symbol", "ticker", "ma_ck", "mack")
                price_col = _find_col("match_price", "last_price", "close_price", "giaKhopLenh")
                chg_pct_col = _find_col("change_percent", "pct_change", "percent")
                ref_col = _find_col("ref_price", "reference")

                if sym_col and price_col:
                    for _, row in board.iterrows():
                        sym = str(row[sym_col])
                        if sym not in symbols:
                            continue
                        price = pd.to_numeric(row[price_col], errors="coerce")
                        chg = None
                        if chg_pct_col is not None:
                            chg = pd.to_numeric(row[chg_pct_col], errors="coerce")
                            if pd.notna(chg) and abs(chg) > 1:  # API trả theo % (vd 2.5) chứ không phải tỉ lệ
                                chg = chg / 100
                        elif ref_col is not None:
                            ref = pd.to_numeric(row[ref_col], errors="coerce")
                            chg = (price / ref - 1) if ref else None
                        rows.append({"Mã": sym, "Giá": float(price) if pd.notna(price) else None,
                                      "% Thay đổi": float(chg) if chg is not None and pd.notna(chg) else None})
        except Exception:
            pass

        found_syms = {r["Mã"] for r in rows}
        for sym in symbols:
            if sym not in found_syms:
                # Không fallback gọi lại từng mã ở đây: vnstock tự retry/backoff khá lâu
                # mỗi lần gọi, nên dồn 10 lần gọi tuần tự có thể khiến cả trang treo rất
                # lâu khi API đang bị giới hạn. Chấp nhận thiếu dữ liệu (hiện "—") thay vì
                # kéo dài thời gian tải — người dùng có thể xem chi tiết mã đó ở "Một tài sản".
                rows.append({"Mã": sym, "Giá": None, "% Thay đổi": None})
        # sắp xếp lại đúng thứ tự Top 10 gốc
        order = {s: i for i, s in enumerate(symbols)}
        rows.sort(key=lambda r: order.get(r["Mã"], 999))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tin vĩ mô/lãi suất/thị trường chung — dùng cho banner chạy chữ ở đầu trang
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def get_macro_headlines(limit_per_source: int = 4) -> list:
    """
    Tổng hợp tin tức mang tính vĩ mô/thị trường chung (lãi suất, chính sách tiền tệ,
    diễn biến lớn của thị trường...) từ vài nguồn đại diện:
        - Thị trường thế giới: tin gắn với chỉ số S&P 500 (^GSPC) — Yahoo Finance
          thường gắn cả tin vĩ mô lớn (Fed, lãi suất...) vào tin của chỉ số.
        - Crypto: tin gắn với Bitcoin (BTC-USD).
        - Việt Nam: tin gắn với một ngân hàng lớn (VCB) làm đại diện — vnstock chưa có
          endpoint tin vĩ mô/NHNN riêng biệt nên đây là lựa chọn best-effort.
    Trả về list[dict]: {"title":, "link":, "tag":} — tag để gắn nhãn nguồn trên banner.
    """
    headlines = []
    sources = [
        (ASSET_WORLD, "^GSPC", "🌍 Thế giới"),
        (ASSET_CRYPTO, "BTC-USD", "🪙 Crypto"),
        (ASSET_VN, "VCB", "🇻🇳 Việt Nam"),
    ]
    for ac, sym, tag in sources:
        try:
            items = get_news(ac, sym, limit=limit_per_source)
            for it in items:
                it["tag"] = tag
            headlines.extend(items)
        except Exception:
            continue
    return headlines
