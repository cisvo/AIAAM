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
        tables = pd.read_html(resp.text)
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
        tables = pd.read_html(requests.get(url, headers=headers, timeout=8).text)
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
