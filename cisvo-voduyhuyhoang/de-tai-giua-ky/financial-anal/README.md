# FinDash-VN — Dashboard thông tin đầu tư có hỗ trợ Chatbot

Dashboard xây trên nền `findash_app.py` mẫu của thầy, mở rộng để đáp ứng đầy đủ yêu cầu:

| Yêu cầu đề bài | Vị trí trong code |
|---|---|
| [1] Summary (chọn từ danh sách CP thế giới / VN) | `render_summary_tab()` trong `app.py` |
| [2] Chart: giá + khối lượng, sampling ngày/tuần/tháng, Line/Candlestick | `render_chart_tab()` |
| [3] Thống kê, tài chính, phân tích 1 CP | `render_stats_financials_tab()`, `render_analysis_tab()` |
| [4] Phân tích danh mục: CAPM, APT, biểu đồ/thống kê/chỉ số | `render_capm_tab()`, `render_apt_tab()`, `render_portfolio_stats_tab()`, module `portfolio_analytics.py` |
| [5] Monte Carlo Simulation (danh mục) | `render_monte_carlo_tab()`, `pa.monte_carlo_portfolio()` |
| Hỗ trợ chatbot | `render_chatbot_mode()`, module `chatbot.py` (dùng Anthropic Claude API) |

Hỗ trợ 3 loại tài sản: **Cổ phiếu Thế giới** (yfinance), **Cổ phiếu Việt Nam** (vnstock v4,
nguồn VCI/KBS), **Tiền điện tử** (yfinance, mã dạng `BTC-USD`).

## Cấu trúc project

```
findash_vn/
├── app.py                  # Streamlit UI chính — 3 chế độ: Một tài sản / Danh mục / Chatbot
├── data_sources.py         # Lớp truy xuất dữ liệu hợp nhất cho cả 3 loại tài sản
├── portfolio_analytics.py  # CAPM, APT, thống kê danh mục, Monte Carlo Simulation, VaR/CVaR
├── chatbot.py               # Tích hợp Anthropic Claude API, có ngữ cảnh từ dashboard
├── requirements.txt
└── README.md
```

## Cài đặt & chạy

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Ứng dụng cần **kết nối Internet** để gọi Yahoo Finance và vnstock — sandbox lúc build
không có mạng ra ngoài nên phần fetch dữ liệu thật (giá, báo cáo tài chính...) mới chỉ
được kiểm thử bằng dữ liệu mô phỏng (`portfolio_analytics.py` đã test bằng số liệu giả
lập, `app.py` đã khởi động thành công qua `streamlit run`) — bạn cần chạy thử ở máy có
mạng để xác nhận phần gọi API thật (yfinance/vnstock) trả đúng dữ liệu, vì các nguồn này
đôi khi đổi cấu trúc response.

## Ghi chú quan trọng

- **vnstock**: bản v4+ dùng class `Quote`, `Company`, `Finance`, `Listing`
  (`from vnstock import Quote, Company, Finance, Listing`). Chế độ khách (không có API
  key) giới hạn ~20 request/phút, ~4 kỳ báo cáo tài chính. Nếu cần nhiều hơn, đăng ký
  API key miễn phí tại vnstocks.com rồi gọi `vnstock.register_user(api_key=...)` ở đầu
  `app.py`.
- **Chatbot**: người dùng tự nhập Anthropic API key ở sidebar (chỉ lưu trong phiên làm
  việc, không hard-code trong source). Model mặc định `claude-sonnet-5` — có thể đổi
  trong ô "Model" ở sidebar.
- **APT**: dùng bản đơn giản hoá — hồi quy đa nhân tố với các nhân tố quan sát được
  (thị trường, giá dầu, giá vàng, chỉ số USD...) thay vì bộ nhân tố Fama-French đầy đủ,
  vì dữ liệu Fama-French không có sẵn miễn phí cho thị trường Việt Nam. Phù hợp mục đích
  học tập; có thể mở rộng thêm nhân tố trong `render_apt_tab()`.
- **Trộn tài sản nhiều loại tiền tệ trong 1 danh mục** (VD: cổ phiếu VN bằng VND + Bitcoin
  bằng USD): phần tính toán dùng **lợi suất phần trăm** (không quy đổi tuyệt đối theo tỉ
  giá), nên tỉ trọng danh mục là tỉ trọng theo % giá trị đầu tư giả định, không phải quy
  đổi ngoại tệ chính xác — đây là một đơn giản hoá hợp lý cho mục đích học tập, nên nêu rõ
  giả định này trong báo cáo nộp bài.
- Monte Carlo Simulation ở đây mô phỏng **ở cấp danh mục** (theo đúng yêu cầu đề bài, mục
  [5] nằm trong nhóm "Danh mục đầu tư"), dùng phân rã Cholesky trên ma trận hiệp phương
  sai lịch sử để tạo lợi suất mô phỏng có tương quan giữa các tài sản — khác với Monte
  Carlo đơn tài sản trong `findash_app.py` mẫu (vốn không tính tương quan).

## Có thể mở rộng thêm

- Thêm nhân tố Fama-French thật (nếu tìm được nguồn dữ liệu công khai cho VN).
- Thêm xác thực `register_user()` cho vnstock để tăng giới hạn request.
- Cache dữ liệu ra file/DB để giảm số lần gọi API khi demo trên lớp.
- Thêm tối ưu hoá danh mục (Markowitz efficient frontier) dựa trên `portfolio_stats()`
  đã có sẵn ma trận hiệp phương sai.
