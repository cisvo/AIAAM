# FinDash-VN — Dashboard thông tin đầu tư có hỗ trợ Chatbot

Dashboard xây trên nền `findash_app.py` mẫu của thầy, đáp ứng đủ 6 yêu cầu đề bài,
cộng thêm một loạt tính năng nâng cao của Streamlit để giao diện phong phú hơn.

## Đáp ứng đề bài

| Yêu cầu đề bài | Vị trí trong code |
|---|---|
| [1] Summary (chọn từ danh sách CP thế giới / VN) | `render_summary_tab()` |
| [2] Chart: giá + khối lượng, sampling ngày/tuần/tháng, Line/Candlestick | `render_chart_tab()` |
| [3] Thống kê, tài chính, phân tích 1 CP | `render_stats_financials_tab()`, `render_analysis_tab()` |
| [4] Phân tích danh mục: CAPM, APT, biểu đồ/thống kê/chỉ số | `render_capm_tab()`, `render_apt_tab()`, `render_portfolio_stats_tab()`, `portfolio_analytics.py` |
| [5] Monte Carlo Simulation (danh mục) | `render_monte_carlo_tab()`, `pa.monte_carlo_portfolio()` |
| Hỗ trợ chatbot | `page_chatbot()`, `chatbot.py` (Anthropic Claude API) |

## Tính năng Streamlit nâng cao đã thêm

| Tính năng | Dùng ở đâu | Ghi chú |
|---|---|---|
| **Multipage app** (`st.Page` / `st.navigation`) | `main()` trong `app.py` | 3 trang có URL riêng: `/single-asset`, `/portfolio`, `/chatbot` |
| **st.fragment** | Các hàm `render_*_tab` nặng (Chart, CAPM, APT, Monte Carlo...) | Đổi input trong 1 tab chỉ rerun tab đó, không rerun toàn trang |
| **st.fragment(run_every=...)** | `_live_price_ticker()` | Bật nút "🔴 Live" ở Summary để tự làm mới giá mỗi 30 giây |
| **st.dialog** | `quick_lookup_dialog()` | Nút "🔍 Xem mã khác" ở sidebar — tra cứu nhanh 1 mã khác dạng popup |
| **st.status** | Trong các bước tải dữ liệu (Summary, Chart, Tài chính, Danh mục) | Hiện tiến trình "Đang tải...Đã tải xong" |
| **st.data_editor** | Bảng tỉ trọng danh mục trong `page_portfolio()` | Sửa % tỉ trọng trực tiếp trong bảng |
| **st.file_uploader** | Expander "Nạp danh mục từ CSV" trong `page_portfolio()` | Cột cần có: `asset_class` (world/vn/crypto), `symbol`, `weight` |
| **st.download_button** (CSV/Excel/PDF) | `ui_helpers.py`, dùng khắp Summary/Chart/Tài chính/Danh mục | PDF vẽ bằng matplotlib để giữ đúng dấu tiếng Việt |
| **streamlit-aggrid** | `ui_helpers.show_table()` | Bảng sort/filter kiểu Excel; tự fallback về `st.dataframe` nếu chưa cài |
| **Theming + st.logo** | `.streamlit/config.toml`, `assets/logo.png`, `assets/icon.png` | Theme tối, logo tự tạo bằng PIL |
| **st.login() / cổng mật khẩu** | `auth.py` | 3 chế độ: `none` (mặc định) / `password` / `oidc` (Google) |
| **Bản đồ phân bổ danh mục** | `render_geo_tab()` (tab "🗺️ Phân bổ địa lý") | Dùng `country` từ yfinance (World) / cố định "Vietnam" cho CP VN; crypto không có quốc gia |

## Cấu trúc project

```
findash_vn/
├── app.py                     # Streamlit UI chính — multipage, fragment, dialog, status...
├── data_sources.py            # Lớp truy xuất dữ liệu hợp nhất cho cả 3 loại tài sản
├── portfolio_analytics.py     # CAPM, APT, thống kê danh mục, Monte Carlo Simulation, VaR/CVaR
├── chatbot.py                  # Tích hợp Anthropic Claude API, có ngữ cảnh từ dashboard
├── ui_helpers.py               # Bảng AgGrid (có fallback) + xuất báo cáo CSV/Excel/PDF
├── auth.py                     # Cổng đăng nhập tuỳ chọn (none / password / Google OIDC)
├── assets/
│   ├── logo.png                # Logo hiển thị đầu sidebar
│   └── icon.png                # Icon khi sidebar thu gọn
├── .streamlit/
│   ├── config.toml             # Theme tối (navy + vàng gold)
│   └── secrets.toml.example    # Mẫu file bí mật — copy thành secrets.toml rồi điền thật
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

Ứng dụng cần **kết nối Internet** để gọi Yahoo Finance và vnstock. Trong sandbox lúc
build không có mạng ra ngoài, nên các phần đã kiểm thử được là: biên dịch cú pháp toàn
bộ file, chạy `streamlit run app.py` thành công (cả 3 trang `/single-asset`,
`/portfolio`, `/chatbot` trả về HTTP 200, log server không có lỗi), và test riêng
`portfolio_analytics.py` (CAPM/APT/Monte Carlo/VaR) bằng dữ liệu mô phỏng — chạy đúng.
Phần gọi API thật (giá, báo cáo tài chính, quốc gia công ty...) cần bạn tự chạy thử ở
máy có mạng để xác nhận, vì các nguồn này thỉnh thoảng đổi cấu trúc response.

## Cấu hình các tính năng tuỳ chọn

### Đăng nhập (auth.py)
Mặc định `AUTH_MODE = "none"` (không cần đăng nhập, phù hợp lúc demo/nộp bài). Đổi
thành `"password"` để bật cổng mật khẩu chung — nhớ copy
`.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml` và điền
`[auth] password = "..."`. Đổi thành `"oidc"` để bật đăng nhập Google thật — cần đăng
ký OAuth Client tại [Google Cloud Console](https://console.cloud.google.com/) (loại
"Web application", Authorized redirect URI = `http://localhost:8501/oauth2callback`
khi chạy local), sau đó điền `redirect_uri`, `cookie_secret`, và mục `[auth.google]`
(`client_id`, `client_secret`, `server_metadata_url`) vào `secrets.toml` theo mẫu.

### Chatbot
Nhập Anthropic API key ở sidebar khi vào trang Chatbot (chỉ lưu trong phiên làm việc).
Muốn khỏi nhập lại mỗi lần, có thể đặt sẵn `[anthropic] api_key = "sk-ant-..."` trong
`secrets.toml` — app sẽ tự điền vào ô nhập.

### vnstock
Bản v4+ dùng class `Quote`, `Company`, `Finance`, `Listing`
(`from vnstock import Quote, Company, Finance, Listing`). Chế độ khách (không có API
key) giới hạn ~20 request/phút, ~4 kỳ báo cáo tài chính. Cần nhiều hơn thì đăng ký API
key miễn phí tại vnstocks.com rồi gọi `vnstock.register_user(api_key=...)`.

## Ghi chú quan trọng / giả định

- **APT**: bản đơn giản hoá — hồi quy đa nhân tố với các nhân tố quan sát được (thị
  trường, giá dầu, giá vàng, chỉ số USD...) thay vì bộ nhân tố Fama-French đầy đủ, vì
  dữ liệu Fama-French không có sẵn miễn phí cho thị trường Việt Nam.
- **Trộn tài sản nhiều loại tiền tệ trong 1 danh mục** (VD: CP VN bằng VND + Bitcoin
  bằng USD): tính toán dùng **lợi suất phần trăm**, không quy đổi tuyệt đối theo tỉ
  giá — nên nêu rõ giả định này khi nộp bài.
- **Bản đồ phân bổ địa lý**: phụ thuộc trường `country` trong dữ liệu `yfinance`, có
  thể thiếu với một số mã — phần này mang tính minh hoạ, không phải dữ liệu chính xác
  tuyệt đối.
- **PDF xuất báo cáo**: vẽ bằng `matplotlib` (không dùng `fpdf2`) vì font mặc định của
  matplotlib (DejaVu Sans) hiển thị đúng dấu tiếng Việt, còn font Latin-1 mặc định của
  fpdf2 thì mất dấu.
- **streamlit-aggrid**: nếu cài lỗi hoặc không tương thích môi trường, `ui_helpers.show_table()`
  tự động rơi về `st.dataframe` — không làm app crash.

## Có thể mở rộng thêm

- Nhân tố Fama-French thật (nếu tìm được nguồn dữ liệu công khai cho VN).
- Tối ưu hoá danh mục (Markowitz efficient frontier) dựa trên ma trận hiệp phương sai
  đã có sẵn trong `portfolio_stats()`.
- Cache dữ liệu ra file/DB để giảm số lần gọi API khi demo trên lớp.
- Kết nối `st.login()` với Microsoft/Auth0 thay vì chỉ Google (xem `st.login()` docs).
