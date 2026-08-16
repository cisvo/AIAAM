"""
portfolio_analytics.py
=======================
Các hàm phân tích danh mục đầu tư: CAPM, APT (đa nhân tố), thống kê danh mục
(lợi suất kỳ vọng, độ biến động, Sharpe, ma trận tương quan) và Monte Carlo
Simulation cấp danh mục (dùng phân rã Cholesky để mô phỏng lợi suất tương quan).

Quy ước: mọi lợi suất (return) trong module này là log-return theo ngày,
trừ khi ghi chú khác.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize

TRADING_DAYS = 252


def prices_to_returns(price_df: pd.DataFrame) -> pd.Series:
    """price_df: DataFrame có cột Date, Close -> Series log-return theo Date."""
    s = price_df.set_index("Date")["Close"].astype(float)
    return np.log(s / s.shift(1)).dropna()


def align_returns(returns_dict: dict) -> pd.DataFrame:
    """Ghép nhiều Series lợi suất theo ngày chung (inner join theo Date)."""
    df = pd.concat(returns_dict, axis=1)
    df.columns = list(returns_dict.keys())
    return df.dropna()


# ---------------------------------------------------------------------------
# CAPM — mô hình định giá tài sản vốn (single-factor: thị trường)
# ---------------------------------------------------------------------------
def capm_analysis(asset_returns: pd.Series, market_returns: pd.Series, rf_annual: float) -> dict:
    """
    Hồi quy: R_asset - Rf = alpha + beta * (R_market - Rf) + eps
    rf_annual: lãi suất phi rủi ro danh nghĩa/năm (vd 0.045 = 4.5%)
    """
    rf_daily = rf_annual / TRADING_DAYS
    df = pd.concat([asset_returns, market_returns], axis=1).dropna()
    df.columns = ["asset", "market"]

    y = df["asset"] - rf_daily
    X = sm.add_constant(df["market"] - rf_daily)
    model = sm.OLS(y, X).fit()
    alpha_daily, beta = model.params.iloc[0], model.params.iloc[1]

    market_premium_annual = df["market"].mean() * TRADING_DAYS - rf_annual
    expected_return_annual = rf_annual + beta * market_premium_annual

    return {
        "beta": float(beta),
        "alpha_annual": float(alpha_daily * TRADING_DAYS),
        "r_squared": float(model.rsquared),
        "expected_return_annual": float(expected_return_annual),
        "market_premium_annual": float(market_premium_annual),
        "regression_df": df,
    }


# ---------------------------------------------------------------------------
# APT — Arbitrage Pricing Theory (đa nhân tố, đơn giản hoá)
# ---------------------------------------------------------------------------
def apt_analysis(asset_returns: pd.Series, factor_returns: pd.DataFrame, rf_annual: float) -> dict:
    """
    Hồi quy đa nhân tố: R_asset - Rf = alpha + sum(beta_i * F_i) + eps
    factor_returns: DataFrame, mỗi cột là lợi suất (log-return theo ngày) của 1 nhân tố
                     (vd: thị trường, giá dầu, giá vàng, tỷ giá USD...)
    """
    rf_daily = rf_annual / TRADING_DAYS
    df = pd.concat([asset_returns.rename("asset"), factor_returns], axis=1).dropna()

    y = df["asset"] - rf_daily
    X = sm.add_constant(df.drop(columns=["asset"]))
    model = sm.OLS(y, X).fit()

    alpha_daily = model.params.iloc[0]
    betas = model.params.iloc[1:]
    factor_premia_annual = df.drop(columns=["asset"]).mean() * TRADING_DAYS
    expected_return_annual = (
        rf_annual + alpha_daily * TRADING_DAYS
        + float((betas.values * factor_premia_annual.values).sum())
    )

    return {
        "betas": betas,
        "alpha_annual": float(alpha_daily * TRADING_DAYS),
        "r_squared": float(model.rsquared),
        "expected_return_annual": float(expected_return_annual),
        "factor_premia_annual": factor_premia_annual,
        "model": model,
    }


# ---------------------------------------------------------------------------
# Thống kê danh mục
# ---------------------------------------------------------------------------
def portfolio_stats(returns_df: pd.DataFrame, weights: np.ndarray, rf_annual: float = 0.0) -> dict:
    """returns_df: mỗi cột là log-return theo ngày của 1 tài sản. weights: tổng = 1."""
    mean_daily = returns_df.mean().values
    cov_daily = returns_df.cov().values

    port_return_annual = float(np.dot(weights, mean_daily) * TRADING_DAYS)
    port_vol_annual = float(np.sqrt(weights @ cov_daily @ weights) * np.sqrt(TRADING_DAYS))
    sharpe = (port_return_annual - rf_annual) / port_vol_annual if port_vol_annual > 0 else np.nan

    return {
        "expected_return_annual": port_return_annual,
        "volatility_annual": port_vol_annual,
        "sharpe_ratio": float(sharpe),
        "corr_matrix": returns_df.corr(),
        "cov_matrix_annual": returns_df.cov() * TRADING_DAYS,
    }


# ---------------------------------------------------------------------------
# Monte Carlo Simulation cấp danh mục
# ---------------------------------------------------------------------------
def monte_carlo_portfolio(returns_df: pd.DataFrame, weights: np.ndarray,
                           n_sims: int = 500, horizon_days: int = 60,
                           initial_value: float = 100.0, seed: int | None = None):
    """
    Mô phỏng giá trị danh mục bằng phân phối chuẩn đa biến: dùng trung bình và
    ma trận hiệp phương sai lịch sử, phân rã Cholesky để tạo ra các cú sốc lợi
    suất có tương quan giữa các tài sản trong danh mục.

    Trả về:
        sim_paths      -> mảng (n_sims, horizon_days): giá trị danh mục theo từng ngày mô phỏng
        ending_values  -> mảng (n_sims,): giá trị danh mục ở cuối kỳ mô phỏng
    """
    rng = np.random.default_rng(seed)
    mean_daily = returns_df.mean().values
    cov_daily = returns_df.cov().values
    n_assets = len(weights)

    try:
        L = np.linalg.cholesky(cov_daily)
    except np.linalg.LinAlgError:
        cov_daily = cov_daily + np.eye(n_assets) * 1e-10
        L = np.linalg.cholesky(cov_daily)

    sim_paths = np.zeros((n_sims, horizon_days))
    for i in range(n_sims):
        z = rng.standard_normal((horizon_days, n_assets))
        correlated_shocks = z @ L.T + mean_daily
        asset_growth = np.cumprod(1 + correlated_shocks, axis=0)
        port_growth = asset_growth @ weights
        sim_paths[i, :] = initial_value * port_growth

    return sim_paths, sim_paths[:, -1]


def value_at_risk(ending_values: np.ndarray, initial_value: float, confidence: float = 0.95) -> dict:
    """VaR & CVaR tuyệt đối (đơn vị giá trị) tại mức tin cậy (vd 0.95 = 95%)."""
    pct = (1 - confidence) * 100
    threshold = float(np.percentile(ending_values, pct))
    var = initial_value - threshold
    tail_losses = ending_values[ending_values <= threshold]
    cvar = initial_value - float(tail_losses.mean()) if len(tail_losses) > 0 else var
    return {"threshold_value": threshold, "VaR": var, "CVaR": cvar}


# ---------------------------------------------------------------------------
# Chỉ số rủi ro nâng cao: Max Drawdown, Sortino Ratio, Calmar Ratio
# ---------------------------------------------------------------------------
def portfolio_equity_curve(returns_df: pd.DataFrame, weights: np.ndarray,
                            initial_value: float = 100.0) -> pd.Series:
    """Đường giá trị danh mục theo thời gian, dựa trên lợi suất log lịch sử (mua & giữ, không tái cân bằng)."""
    port_daily_return = returns_df.values @ weights  # log-return danh mục mỗi ngày
    equity = initial_value * np.exp(np.cumsum(port_daily_return))
    return pd.Series(equity, index=returns_df.index)


def max_drawdown(equity_curve: pd.Series) -> dict:
    """Mức sụt giảm tối đa từ đỉnh trước đó. Trả về mdd (số âm) và chuỗi drawdown theo thời gian."""
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    return {"max_drawdown": float(drawdown.min()), "drawdown_series": drawdown}


def sortino_ratio(daily_returns: pd.Series, rf_annual: float) -> float:
    """Giống Sharpe nhưng chỉ phạt độ lệch chuẩn của lợi suất ÂM (downside deviation)."""
    rf_daily = rf_annual / TRADING_DAYS
    excess = daily_returns - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return np.nan
    downside_std = downside.std() * np.sqrt(TRADING_DAYS)
    ann_excess_return = excess.mean() * TRADING_DAYS
    if downside_std == 0 or np.isnan(downside_std):
        return np.nan
    return float(ann_excess_return / downside_std)


def calmar_ratio(annual_return: float, mdd: float) -> float:
    """Lợi suất năm hoá / |Max Drawdown|. Càng cao càng tốt (lợi nhuận cao so với rủi ro sụt giảm)."""
    if mdd == 0 or np.isnan(mdd):
        return np.nan
    return float(annual_return / abs(mdd))


def extended_risk_metrics(returns_df: pd.DataFrame, weights: np.ndarray, rf_annual: float) -> dict:
    """Gói gọn Max Drawdown / Sortino / Calmar cho 1 danh mục đã có tỉ trọng cố định."""
    equity = portfolio_equity_curve(returns_df, weights)
    port_daily_return = pd.Series(returns_df.values @ weights, index=returns_df.index)
    mdd_res = max_drawdown(equity)
    annual_return = float(port_daily_return.mean() * TRADING_DAYS)
    sortino = sortino_ratio(port_daily_return, rf_annual)
    calmar = calmar_ratio(annual_return, mdd_res["max_drawdown"])
    return {
        "equity_curve": equity,
        "drawdown_series": mdd_res["drawdown_series"],
        "max_drawdown": mdd_res["max_drawdown"],
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
    }


# ---------------------------------------------------------------------------
# Tối ưu hoá danh mục — Markowitz Mean-Variance (không bán khống, w >= 0)
# ---------------------------------------------------------------------------
def _portfolio_variance(w: np.ndarray, cov_annual: np.ndarray) -> float:
    return float(w @ cov_annual @ w)


def optimize_min_variance(returns_df: pd.DataFrame) -> dict:
    """Tìm tỉ trọng có độ biến động (variance) thấp nhất."""
    n = returns_df.shape[1]
    cov_annual = returns_df.cov().values * TRADING_DAYS
    mean_annual = returns_df.mean().values * TRADING_DAYS
    w0 = np.repeat(1 / n, n)
    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    res = minimize(_portfolio_variance, w0, args=(cov_annual,), method="SLSQP",
                    bounds=bounds, constraints=constraints)
    w = res.x
    return {
        "weights": dict(zip(returns_df.columns, w)),
        "expected_return_annual": float(w @ mean_annual),
        "volatility_annual": float(np.sqrt(w @ cov_annual @ w)),
        "success": bool(res.success),
    }


def optimize_max_sharpe(returns_df: pd.DataFrame, rf_annual: float) -> dict:
    """Tìm tỉ trọng có Sharpe Ratio cao nhất (danh mục tiếp tuyến)."""
    n = returns_df.shape[1]
    mean_annual = returns_df.mean().values * TRADING_DAYS
    cov_annual = returns_df.cov().values * TRADING_DAYS

    def neg_sharpe(w):
        ret = w @ mean_annual
        vol = np.sqrt(w @ cov_annual @ w)
        return -(ret - rf_annual) / vol if vol > 0 else 1e6

    w0 = np.repeat(1 / n, n)
    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints)
    w = res.x
    ret = float(w @ mean_annual)
    vol = float(np.sqrt(w @ cov_annual @ w))
    return {
        "weights": dict(zip(returns_df.columns, w)),
        "expected_return_annual": ret,
        "volatility_annual": vol,
        "sharpe_ratio": float((ret - rf_annual) / vol) if vol > 0 else np.nan,
        "success": bool(res.success),
    }


def efficient_frontier_curve(returns_df: pd.DataFrame, n_points: int = 25) -> pd.DataFrame:
    """Vẽ đường biên hiệu quả: với mỗi mức lợi suất mục tiêu, tìm độ biến động nhỏ nhất có thể."""
    n = returns_df.shape[1]
    mean_annual = returns_df.mean().values * TRADING_DAYS
    cov_annual = returns_df.cov().values * TRADING_DAYS
    targets = np.linspace(mean_annual.min(), mean_annual.max(), n_points)

    rows = []
    for t in targets:
        w0 = np.repeat(1 / n, n)
        bounds = [(0.0, 1.0)] * n
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, t=t: w @ mean_annual - t},
        ]
        res = minimize(_portfolio_variance, w0, args=(cov_annual,), method="SLSQP",
                        bounds=bounds, constraints=constraints)
        if res.success:
            vol = float(np.sqrt(res.x @ cov_annual @ res.x))
            rows.append({"target_return": float(t), "volatility": vol})
    return pd.DataFrame(rows)


def random_portfolios(returns_df: pd.DataFrame, n: int = 3000, rf_annual: float = 0.0,
                       seed: int | None = None) -> pd.DataFrame:
    """Sinh ngẫu nhiên n danh mục (tỉ trọng Dirichlet, luôn >=0 và tổng = 1) để vẽ đám mây risk/return."""
    rng = np.random.default_rng(seed)
    n_assets = returns_df.shape[1]
    mean_annual = returns_df.mean().values * TRADING_DAYS
    cov_annual = returns_df.cov().values * TRADING_DAYS

    w = rng.dirichlet(np.ones(n_assets), size=n)
    rets = w @ mean_annual
    vols = np.sqrt(np.einsum("ij,jk,ik->i", w, cov_annual, w))
    sharpes = (rets - rf_annual) / vols
    return pd.DataFrame({"return": rets, "volatility": vols, "sharpe": sharpes})
