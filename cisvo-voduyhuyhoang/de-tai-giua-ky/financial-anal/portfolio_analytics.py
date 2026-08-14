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
