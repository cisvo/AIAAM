# FinDash-VN — Dashboard thông tin đầu tư có hỗ trợ Chatbot

Dashboard xây trên nền `findash_app.py` mẫu của thầy, đáp ứng đủ 6 yêu cầu đề bài,
cộng thêm tính năng giao diện Streamlit nâng cao và một loạt công cụ phân tích đầu tư
thực chất (tối ưu hoá danh mục, chỉ báo kỹ thuật, định giá, backtest...).

## Đáp ứng đề bài

| Yêu cầu đề bài | Vị trí trong code |
|---|---|
| [1] Summary (chọn từ danh sách CP thế giới / VN) | `render_summary_tab()` |
| [2] Chart: giá + khối lượng, sampling ngày/tuần/tháng, Line/Candlestick | `render_chart_tab()` |
| [3] Thống kê, tài chính, phân tích 1 CP | `render_stats_financials_tab()`, `render_analysis_tab()` |
| [4] Phân tích danh mục: CAPM, APT, biểu đồ/thống kê/chỉ số | `render_capm_tab()`, `render_apt_tab()`, `render_portfolio_stats_tab()`, `portfolio_analytics.py` |
| [5] Monte Carlo Simulation (danh mục) | `render_monte_carlo_tab()`, `pa.monte_carlo_portfolio()` |
| Hỗ trợ chatbot | `page_chatbot()`, `chatbot.py` (Anthropic Claude API) |

## Công cụ phân tích đầu tư thực chất (thêm sau khi thầy góp ý bản đầu "quá đơn giản")

| Tính năng | Vị trí | Ghi chú |
|---|---|---|
| **Tối ưu hoá danh mục (Efficient Frontier)** | Tab "🎯 Tối ưu hoá" trong Danh mục đầu tư | Markowitz mean-variance (không bán khống); tìm danh mục Min Variance & Max Sharpe, vẽ đường biên hiệu quả, nút "Áp dụng" để điền tỉ trọng tối ưu vào bảng |
| **Quy đổi ngoại tệ chuẩn (USD/VND)** | Sidebar "Đơn vị tiền tệ chung" trong Danh mục đầu tư | Quy đổi giá CP VN (VND) và CP thế giới/crypto (USD) về 1 đơn vị tiền tệ chung TRƯỚC khi tính lợi suất — khắc phục giả định đơn giản hoá của bản đầu (`data_sources.convert_price_series`, `get_fx_history`) |
| **Chỉ số rủi ro nâng cao** | Tab "📊 Thống kê danh mục" | Max Drawdown, Sortino Ratio, Calmar Ratio + biểu đồ đường giá trị danh mục & drawdown theo thời gian (`pa.extended_risk_metrics`) |
| **Chỉ báo kỹ thuật** | Tab "📈 Chart" (Một tài sản) | RSI(14), MACD, Bollinger Bands — chọn qua multiselect, tự thêm dòng biểu đồ phụ (`technical_indicators.py`) |
| **Định giá DCF / Graham Number** | Tab "💰 Định giá" (Một tài sản) | Graham Number (√(22.5×EPS×BVPS)), DCF 2 giai đoạn với input tự điền best-effort từ dữ liệu công ty (`valuation.py`) |
| **Backtest chiến lược đơn giản** | Tab "🧪 Backtest" (Một tài sản) | SMA Crossover long-only so với Mua & Giữ, không tính phí giao dịch (`backtest.py`) |
| **Tin tức + AI tóm tắt tác động** | Tab "📰 Tin tức" (Một tài sản) | Lấy tiêu đề tin gần đây, nút "Tóm tắt bằng AI" gọi Claude đánh giá tác động (`chatbot.summarize_news`) |

## Tính năng giao diện Streamlit nâng cao

| Tính năng | Vị trí | Ghi chú |
|---|---|---|
| **Multipage app** (`st.Page`/`st.navigation`) | `main()` | 3 trang có URL riêng: `/single-asset`, `/portfolio`, `/chatbot` |
| **st.fragment** | Các tab nặng (Chart, CAPM, APT, Monte Carlo, Tối ưu hoá...) | Đổi input trong 1 tab chỉ rerun tab đó |
| **st.fragment(run_every=...)** | Nút "🔴 Live" ở Summary | Tự làm mới giá mỗi 30 giây |
| **st.dialog** | Nút "🔍 Xem mã khác" | Tra cứu nhanh 1 mã khác dạng popup |
| **st.status** | Mọi bước tải dữ liệu | Hiện tiến trình "Đang tải...Đã tải xong" |
| **st.data_editor** | Bảng tỉ trọng danh mục | Sửa % trực tiếp trong bảng, hoặc nhận tỉ trọng tối ưu tự động điền |
| **st.file_uploader** | Expander "Nạp danh mục từ CSV" | Cột: `asset_class` (world/vn/crypto), `symbol`, `weight` |
| **st.download_button** (CSV/Excel/PDF) | `ui_helpers.py` | PDF vẽ bằng matplotlib để giữ đúng dấu tiếng Việt |
| **streamlit-aggrid** | `ui_helpers.show_table()` | Bảng sort/filter kiểu Excel, tự fallback về `st.dataframe` nếu chưa cài |
| **Theming + st.logo** | `.streamlit/config.toml`, `assets/` | Theme tối, logo tự tạo bằng PIL |
| **st.login() / cổng mật khẩu** | `auth.py` | 3 chế độ: `none` (mặc định) / `password` / `oidc` (Google) |
| **Bản đồ phân bổ danh mục** | Tab "🗺️ Phân bổ địa lý" | Best-effort theo trường `country` của yfinance |

## Cấu trúc project

```
findash_vn/
├── app.py                     # Streamlit UI chính — multipage, fragment, dialog, status...
├── data_sources.py            # Truy xuất dữ liệu hợp nhất + FX + tin tức + input định giá
├── portfolio_analytics.py     # CAPM, APT, Monte Carlo, VaR/CVaR, tối ưu hoá, rủi ro nâng cao
├── technical_indicators.py    # RSI, MACD, Bollinger Bands
├── valuation.py                # Graham Number, DCF
├── backtest.py                 # Backtest SMA Crossover vs Mua & Giữ
├── chatbot.py                   # Anthropic Claude API + tóm tắt tin tức
├── ui_helpers.py                # Bảng AgGrid (fallback) + xuất báo cáo CSV/Excel/PDF
├── auth.py                      # Cổng đăng nhập tuỳ chọn (none / password / Google OIDC)
├── assets/
│   ├── logo.png
│   └── icon.png
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
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

## Đã kiểm thử những gì

Sandbox lúc build không có mạng ra ngoài Yahoo Finance/vnstock, nên phần dữ liệu thật
(giá, báo cáo tài chính, tin tức...) bạn cần tự chạy ở máy có mạng để xác nhận. Những gì
đã kiểm thử được trong sandbox:

- Biên dịch cú pháp toàn bộ 9 file Python.
- Test logic độc lập bằng dữ liệu mô phỏng cho toàn bộ module phân tích: CAPM, APT,
  Monte Carlo, VaR/CVaR, tối ưu hoá danh mục (Min Variance/Max Sharpe/Efficient Frontier),
  Max Drawdown/Sortino/Calmar, RSI/MACD/Bollinger, Graham Number/DCF, backtest SMA,
  quy đổi ngoại tệ — tất cả chạy đúng logic, có assertion kiểm tra tính hợp lệ
  (VD: tổng tỉ trọng tối ưu = 100%, RSI trong khoảng 0-100, Bollinger upper ≥ mid ≥ lower...).
- Dùng `streamlit.testing.v1.AppTest` (chạy thực sự script Python phía server, khác với
  `curl` chỉ tải khung HTML tĩnh) để execute cả 3 trang — phát hiện và **sửa 1 lỗi thật**:
  `st.secrets` bị lỗi khi chưa có `secrets.toml` (ở trang Chatbot và `auth.py` chế độ
  password); đã bọc try/except, chạy lại xác nhận không còn exception ở cả 3 trang.
- Chạy `streamlit run app.py` thật và `curl` cả 3 route — trả về HTTP 200.

## Cấu hình các tính năng tuỳ chọn

### Đăng nhập (auth.py)
Mặc định `AUTH_MODE = "none"`. Đổi `"password"` để bật cổng mật khẩu chung (copy
`.streamlit/secrets.toml.example` → `secrets.toml`, điền `[auth] password = "..."`).
Đổi `"oidc"` để bật đăng nhập Google thật — cần đăng ký OAuth Client tại Google Cloud
Console và điền `redirect_uri`, `cookie_secret`, `[auth.google]` vào `secrets.toml`.

### Chatbot & tóm tắt tin tức bằng AI
Nhập Anthropic API key ở sidebar trang Chatbot (dùng chung cho cả tính năng "Tóm tắt tin
tức bằng AI" ở tab Tin tức, vì cùng lưu trong session). Có thể đặt sẵn
`[anthropic] api_key = "..."` trong `secrets.toml` để khỏi nhập lại.

### vnstock
Bản v4+ dùng class `Quote`, `Company`, `Finance`, `Listing`. Chế độ khách giới hạn ~20
request/phút, ~4 kỳ báo cáo tài chính. Cần nhiều hơn thì `vnstock.register_user(api_key=...)`.

## Ghi chú quan trọng / giả định

- **APT**: bản đơn giản hoá — hồi quy đa nhân tố với nhân tố quan sát được (thị trường,
  dầu, vàng, USD Index) thay vì Fama-French đầy đủ (không có sẵn miễn phí cho VN).
- **Quy đổi ngoại tệ**: dùng tỉ giá `VND=X` từ Yahoo Finance theo ngày; nếu không lấy được
  tỉ giá cho 1 ngày cụ thể sẽ dùng giá trị gần nhất (forward/backward fill).
- **DCF/Graham Number**: công cụ minh hoạ, độ nhạy rất cao với giả định — số liệu tự động
  điền (EPS, BVPS, FCF, số CP lưu hành) là best-effort, nên tự kiểm tra lại trước khi dùng.
- **Backtest**: không tính phí giao dịch/trượt giá/thuế — kết quả thực tế sẽ thấp hơn.
- **Tin tức**: cấu trúc response của Yahoo Finance (`yfinance`) và vnstock cho phần tin tức
  có thể thay đổi theo thời gian vì đây là endpoint không chính thức — nếu không lấy được
  tin, đó là lỗi nguồn dữ liệu bên ngoài, không phải lỗi code.
- **Bản đồ phân bổ địa lý**: phụ thuộc trường `country` trong `yfinance`, có thể thiếu với
  một số mã — mang tính minh hoạ.
- **streamlit-aggrid**: nếu cài lỗi hoặc không tương thích môi trường, `ui_helpers.show_table()`
  tự động rơi về `st.dataframe`.

## Có thể mở rộng thêm

- Nhân tố Fama-French thật (nếu tìm được nguồn dữ liệu công khai cho VN).
- Backtest với phí giao dịch, nhiều chiến lược hơn (RSI, MACD crossover...).
- Rebalancing theo lịch (định kỳ đưa danh mục về tỉ trọng mục tiêu).
- Cache dữ liệu ra file/DB để giảm số lần gọi API khi demo trên lớp.
