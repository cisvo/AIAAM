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

## Công cụ phân tích đầu tư thực chất

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

## UI

Streamlit theming mặc định chỉ đổi màu, không đổi hình khối/khoảng cách — nên bản đầu
nhìn phẳng, rời rạc. Đã sửa bằng **cấu hình chính thức của Streamlit** (không phải CSS
hack):

- `.streamlit/config.toml`: thêm `baseRadius="large"` (bo góc mọi input/button/card/
  dataframe), `borderColor` + `showWidgetBorder=true` (viền nhẹ quanh widget kể cả khi
  không focus — hết cảm giác "mọi thứ trôi nổi"), `showSidebarBorder=true`, và màu nền
  sidebar riêng (`[theme.sidebar]`) để tách biệt trực quan với nội dung chính.
- Gom các nhóm điều khiển liên quan vào `st.container(border=True)` (card thật, API gốc
  của Streamlit) thay vì để từng widget trôi nổi rời rạc — VD: khối điều khiển Chart,
  khối chọn danh mục, bảng tỉ trọng, khối Graham/DCF...
- Bỏ các hộp `st.status` full-width cho những lần tải dữ liệu nhanh/đơn lẻ (Summary,
  Chart, Stats, Backtest) — đổi sang `st.spinner` (tự biến mất, không chiếm chỗ khi xong).
  Chỉ giữ `st.status` ở Danh mục đầu tư vì đó là nơi thực sự có nhiều bước tải tuần tự.
- Sửa placeholder tiếng Anh sót lại ("Choose options") bằng `placeholder="Chọn..."` trên
  các multiselect.
- Giảm bớt tiêu đề lặp lại/quá to (`st.title` → `st.subheader`/`st.markdown` ở cấp trang
  và tab) cho đỡ nặng nề.

## Trang chủ (Home) — tổng quan + đề xuất AI

Trang mặc định khi mở app (`page_home()` trong `app.py`). 4 phần:

- **Tỉ trọng danh mục hiện tại**: biểu đồ tròn + Lợi suất kỳ vọng/Độ biến động/Sharpe/Max
  Drawdown — lấy từ lần phân tích gần nhất ở trang "Danh mục đầu tư" (`last_portfolio_weights`,
  `last_portfolio_stats` trong session_state). Chưa phân tích danh mục nào thì hiện nút dẫn sang.
- **🤖 Đánh giá AI theo từng mã**: nút bấm gọi Claude (`chatbot.assess_portfolio()`), đưa
  tỉ trọng + lợi suất kỳ vọng + độ biến động + beta (nếu có từ tab CAPM) của từng mã, AI trả
  về nhãn **🟢 An toàn / 🟡 Cân nhắc / 🔴 Rủi ro cao** kèm 1 câu giải thích. Đây là góc nhìn
  tham khảo diễn giải từ số liệu thống kê — không phải khuyến nghị đầu tư.
- **📰 Tin tức quan trọng**: gộp tin từ các mã trong danh mục (hoặc vài mã tiêu biểu nếu
  chưa có danh mục).
- **💹 Giá thị trường**: 3 tab Top 10 Tiền điện tử / Top 10 CP Việt Nam / Top 10 CP Thế giới,
  tự làm mới định kỳ (`st.fragment(run_every=...)`).

### Vấn đề thật phát hiện được khi build phần Top 10 real-time

Trong lúc test bằng `AppTest`, phát hiện **rate limit thật của vnstock** (gói khách: 20
request/phút, có xác nhận qua log lỗi thật khi vượt hạn mức):

1. **Không auto-refresh bảng VN mỗi 30s như 2 bảng kia** — 10 mã × mỗi 30s sẽ ăn hết sạch
   quota liên tục, làm nghẽn các phần khác của app cũng đang dùng vnstock (Một tài sản,
   Danh mục đầu tư). Đã đổi bảng VN sang làm mới mỗi **90 giây**.
2. **vnstock không có API lấy giá hàng loạt như `yf.download()`** — ban đầu code gọi lặp
   10 lần `Quote.history()` (1 lần/mã), vừa chậm vừa tốn quota. Đã đổi sang dùng
   `Trading(source="VCI").price_board(symbols_list)` — 1 lần gọi cho cả 10 mã. **Lưu ý**:
   tên cột trả về được code tự dò theo từ khoá (symbol/giá khớp lệnh/% thay đổi...) vì
   sandbox lúc build bị vnstock tạm chặn IP (403) sau nhiều lần test, không lấy được response
   thật để xác nhận chính xác tên cột — nếu dò sai, bảng sẽ hiện "—" thay vì giá (không
   crash, nhưng cũng không có dữ liệu). **Bạn cần tự chạy thử ở máy có mạng để xác nhận
   bảng Top 10 VN thật sự hiển thị giá đúng** — nếu không, báo lại để mình chỉnh tên cột.
3. **Bỏ cơ chế fallback gọi lại từng mã khi `price_board` lỗi** — thử ban đầu nhưng phát
   hiện vnstock tự retry/backoff nội bộ khá lâu mỗi lần gọi (có lúc ~7-15s/mã), nên fallback
   10 mã tuần tự có thể khiến cả trang treo hơn 1 phút khi API đang bị giới hạn. Thay vào đó:
   chỉ gọi `price_board` **một lần**, giới hạn thời gian chờ cứng **12 giây**
   (`concurrent.futures` timeout) — quá thời gian thì trả "—" cho các mã chưa có, không để
   treo trang.

## Banner tin vĩ mô chạy chữ

Ngay phía trên nội dung mỗi trang (không phải thanh chrome gốc của Streamlit ở trên
cùng — khu vực đó có nút "Deploy" là do Streamlit kiểm soát, không chỉnh được) là 1
banner chạy chữ ngang kiểu Bloomberg/Reuters, hiện tin vĩ mô/lãi suất/thị trường chung
(`render_market_ticker()` trong `app.py`, gọi 1 lần trong `main()` nên hiện trên mọi trang).

Nội dung lấy từ `data_sources.get_macro_headlines()` — tổng hợp tin từ 3 nguồn đại diện:
- Thế giới: tin gắn với chỉ số S&P 500 (`^GSPC`) — Yahoo Finance thường gắn cả tin vĩ mô
  lớn (Fed, lãi suất...) vào tin của chỉ số.
- Crypto: tin gắn với Bitcoin (`BTC-USD`).
- Việt Nam: tin gắn với 1 ngân hàng lớn (VCB) làm đại diện — vnstock chưa có endpoint
  tin vĩ mô/NHNN riêng biệt nên đây là lựa chọn best-effort, không phải tin NHNN trực tiếp.

Cache 15 phút (`ttl=900`) để không gọi API quá thường xuyên. Nếu không lấy được tin nào
(mất mạng, hết hạn mức API...), banner tự ẩn — không hiện thanh trống.

**Đã kiểm thử**: dùng `wkhtmltoimage` render thử banner với dữ liệu giả ra ảnh PNG để soi
bằng mắt — bố cục, màu sắc, viền bo góc đúng như thiết kế. Hiệu ứng cuộn chữ (CSS
`@keyframes`) là cú pháp chuẩn, phổ biến, không thể chụp ảnh tĩnh để xác nhận chuyển động
nhưng cú pháp đã đúng chuẩn W3C.

## Liên kết giữa 3 trang


Trước đó Chatbot có 1 lỗi thật: luôn đọc `symbol=None` nên chưa từng biết bạn đang xem
mã nào ở "Một tài sản". Đã sửa + thêm điều hướng 2 chiều thật sự:

- **Một tài sản → Chatbot**: nút "💬 Hỏi Chatbot về {mã}" — chuyển thẳng sang Chatbot,
  ngữ cảnh tự động gồm đúng mã + số liệu Summary mới nhất của mã đó.
- **Một tài sản → Danh mục đầu tư**: nút "➕ Thêm {mã} vào danh mục đầu tư" — thêm mã
  đang xem vào danh sách chọn ở trang Danh mục rồi chuyển sang đó luôn.
- **Danh mục đầu tư → Một tài sản**: chọn 1 mã trong danh mục + nút "Xem chi tiết" —
  nhảy sang "Một tài sản" với đúng mã đó đã được chọn sẵn.
- **Danh mục đầu tư → Chatbot**: nút "💬 Hỏi Chatbot về danh mục này" sau khi phân tích
  xong — ngữ cảnh tự gồm tỉ trọng, lợi suất kỳ vọng, Sharpe... của danh mục vừa tính.
- **Chatbot**: hiện rõ đang dùng ngữ cảnh nào (mã nào / danh mục nào), có checkbox tắt
  bớt nếu không muốn gửi, và cảnh báo rõ khi chưa có ngữ cảnh nào để dùng.

Kỹ thuật: dùng `st.switch_page()` (API chính thức của Streamlit cho multipage app) với
3 đối tượng `st.Page` khai báo ở cấp module (`PAGE_SINGLE`, `PAGE_PORTFOLIO`,
`PAGE_CHATBOT`) — không phải tự chế điều hướng bằng session_state. Đã test bằng
`AppTest` mô phỏng click thật cả 2 chiều điều hướng, xác nhận không lỗi và không cảnh báo.

## Cấu trúc project

```
findash_vn/
├── app.py                     # Streamlit UI chính — Trang chủ, multipage, fragment, dialog, status...
├── data_sources.py            # Truy xuất dữ liệu hợp nhất + FX + tin tức + input định giá + bảng giá real-time
├── portfolio_analytics.py     # CAPM, APT, Monte Carlo, VaR/CVaR, tối ưu hoá, rủi ro nâng cao
├── technical_indicators.py    # RSI, MACD, Bollinger Bands
├── valuation.py                # Graham Number, DCF
├── backtest.py                 # Backtest SMA Crossover vs Mua & Giữ
├── chatbot.py                   # Anthropic Claude API + tóm tắt tin tức + đánh giá AI danh mục
├── ui_helpers.py                # Bảng AgGrid (fallback) + xuất báo cáo CSV/Excel/PDF (bảng vẽ bằng matplotlib.table)
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

## TODO: Mở rộng thêm

- Nhân tố Fama-French thật (nếu tìm được nguồn dữ liệu công khai cho VN).
- Backtest với phí giao dịch, nhiều chiến lược hơn (RSI, MACD crossover...).
- Rebalancing theo lịch (định kỳ đưa danh mục về tỉ trọng mục tiêu).
- Cache dữ liệu ra file/DB để giảm số lần gọi API khi demo trên lớp.
