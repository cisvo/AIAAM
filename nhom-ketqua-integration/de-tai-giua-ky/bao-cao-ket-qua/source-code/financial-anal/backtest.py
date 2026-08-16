"""
backtest.py
===========
Backtest chiến lược đơn giản: SMA Crossover (long-only) so với Mua & Giữ (Buy & Hold).

Đây là công cụ minh hoạ học tập: KHÔNG tính phí giao dịch, trượt giá, hay thuế —
kết quả thực tế khi giao dịch thật sẽ thấp hơn.
"""
import numpy as np
import pandas as pd


def sma_crossover_backtest(price_df: pd.DataFrame, fast: int = 20, slow: int = 50,
                            initial_capital: float = 100.0) -> dict:
    """
    price_df: DataFrame có cột Date, Close.
    Chiến lược: giữ vị thế MUA khi SMA nhanh > SMA chậm, đứng ngoài thị trường khi ngược lại.
    Tín hiệu được áp dụng từ phiên KẾ TIẾP sau khi xuất hiện (tránh nhìn trước dữ liệu).

    Trả về dict:
        df       -> DataFrame chi tiết theo ngày (giá, tín hiệu, giá trị 2 chiến lược)
        summary  -> DataFrame so sánh Tổng lợi suất / Lợi suất năm hoá / Max Drawdown
        n_trades -> số lần đổi tín hiệu (ước lượng số giao dịch)
    """
    df = price_df[["Date", "Close"]].copy().reset_index(drop=True)
    df["SMA_fast"] = df["Close"].rolling(fast).mean()
    df["SMA_slow"] = df["Close"].rolling(slow).mean()
    df["signal"] = (df["SMA_fast"] > df["SMA_slow"]).astype(int)
    df["signal"] = df["signal"].shift(1).fillna(0)  # vào lệnh ở phiên sau khi có tín hiệu

    df["daily_return"] = df["Close"].pct_change().fillna(0)
    df["strategy_return"] = df["daily_return"] * df["signal"]

    df["buyhold_equity"] = initial_capital * (1 + df["daily_return"]).cumprod()
    df["strategy_equity"] = initial_capital * (1 + df["strategy_return"]).cumprod()

    n_trades = int((df["signal"].diff().abs() == 1).sum())

    def _total_return(equity):
        return float(equity.iloc[-1] / equity.iloc[0] - 1)

    def _ann_return(equity, n_days):
        total = equity.iloc[-1] / equity.iloc[0]
        years = n_days / 252
        return float(total ** (1 / years) - 1) if years > 0 and total > 0 else np.nan

    def _max_dd(equity):
        running_max = equity.cummax()
        dd = equity / running_max - 1
        return float(dd.min())

    n = len(df)
    summary = pd.DataFrame([
        {"Chỉ số": "Tổng lợi suất", "Chiến lược SMA": _total_return(df["strategy_equity"]),
         "Mua & Giữ": _total_return(df["buyhold_equity"])},
        {"Chỉ số": "Lợi suất năm hoá", "Chiến lược SMA": _ann_return(df["strategy_equity"], n),
         "Mua & Giữ": _ann_return(df["buyhold_equity"], n)},
        {"Chỉ số": "Max Drawdown", "Chiến lược SMA": _max_dd(df["strategy_equity"]),
         "Mua & Giữ": _max_dd(df["buyhold_equity"])},
    ]).set_index("Chỉ số")

    return {"df": df, "summary": summary, "n_trades": n_trades}
