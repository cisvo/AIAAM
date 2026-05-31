# Investment Paper Analyzer

Ứng dụng phân tích papers nghiên cứu đầu tư bằng AI (Claude) với giao diện web.

## Tính năng
- Upload nhiều file PDF papers cùng lúc
- Trích xuất số liệu, thống kê từ papers (Sharpe ratio, CAAR, returns, v.v.)
- Nhận diện tín hiệu đầu tư (BUY / HOLD / SELL / CAUTION)
- Biểu đồ so sánh tự động từ dữ liệu papers
- 5 chế độ phân tích + 8 câu hỏi gợi ý nhanh
- Chat interface hỏi tự do bằng tiếng Việt hoặc tiếng Anh

## Cài đặt

```bash
pip install -r requirements.txt
```

## Cấu hình API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Chạy app

```bash
python app.py
```

Mở trình duyệt tại: http://localhost:7860

## Cách dùng
1. Upload 1 hoặc nhiều file PDF (papers nghiên cứu)
2. Chọn chế độ phân tích ở sidebar trái
3. Nhấn một câu hỏi gợi ý hoặc tự nhập câu hỏi
4. Xem kết quả ở panel phải: biểu đồ + phân tích + tín hiệu đầu tư

## Papers đã test
- Portfolio optimization in the era of digital financialization (Ma et al., 2020)
- Portfolio diversification across cryptocurrencies (Liu, 2019)
- Ảnh hưởng thông báo chi trả cổ tức — dược phẩm Việt Nam (Lê Phương Lan, 2017)

## Công nghệ
| Thư viện | Mục đích |
|----------|----------|
| Gradio | Web UI |
| Anthropic Claude | Phân tích AI |
| pdfplumber | Đọc PDF |
| Plotly | Biểu đồ tương tác |
