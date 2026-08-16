"""
valuation.py
============
Công cụ định giá nhanh: Graham Number và DCF (Discounted Cash Flow) đơn giản hoá.
Đây là công cụ minh hoạ/học tập — không thay thế mô hình định giá chuyên nghiệp
(giả định 1 giai đoạn tăng trưởng, không tính đến rủi ro đặc thù ngành, cấu trúc vốn...).
"""
import numpy as np


def graham_number(eps: float, book_value_per_share: float):
    """
    Công thức Benjamin Graham: sqrt(22.5 x EPS x BVPS)
    Ước tính giá "hợp lý tối đa" cho cổ phiếu giá trị (value investing).
    Trả về None nếu thiếu dữ liệu hoặc EPS/BVPS âm (công ty không phù hợp mô hình này).
    """
    if eps is None or book_value_per_share is None:
        return None
    if eps <= 0 or book_value_per_share <= 0:
        return None
    return float(np.sqrt(22.5 * eps * book_value_per_share))


def dcf_intrinsic_value(fcf0: float, growth_rate: float, discount_rate: float,
                         terminal_growth: float, years: int = 5,
                         shares_outstanding: float | None = None) -> dict | None:
    """
    DCF 2 giai đoạn đơn giản: tăng trưởng đều `growth_rate` trong `years` năm,
    sau đó tăng trưởng vĩnh viễn `terminal_growth` (Gordon Growth Model).

    fcf0              : Free Cash Flow năm gần nhất (đơn vị tiền tệ gốc)
    growth_rate       : tốc độ tăng trưởng FCF trong giai đoạn dự báo (vd 0.10 = 10%/năm)
    discount_rate     : tỉ lệ chiết khấu / WACC (vd 0.12 = 12%)
    terminal_growth   : tốc độ tăng trưởng vĩnh viễn sau giai đoạn dự báo (vd 0.03)
    years             : số năm dự báo rõ ràng
    shares_outstanding: số cổ phiếu lưu hành — nếu có, trả thêm giá trị ước tính/cổ phiếu

    Trả về None nếu discount_rate <= terminal_growth (mô hình không hội tụ).
    """
    if discount_rate <= terminal_growth:
        return None
    if fcf0 is None:
        return None

    pv_fcf = 0.0
    fcf = fcf0
    for t in range(1, years + 1):
        fcf = fcf * (1 + growth_rate)
        pv_fcf += fcf / (1 + discount_rate) ** t

    terminal_value = fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** years
    enterprise_value = pv_fcf + pv_terminal

    result = {
        "enterprise_value": enterprise_value,
        "pv_fcf": pv_fcf,
        "pv_terminal": pv_terminal,
    }
    if shares_outstanding:
        result["value_per_share"] = enterprise_value / shares_outstanding
    return result
