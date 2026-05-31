# Investment Paper Analyzer (Gemini Edition)

Ứng dụng phân tích papers nghiên cứu đầu tư bằng Google Gemini AI.

## Lấy Gemini API Key miễn phí

1. Vào https://aistudio.google.com/apikey
2. Đăng nhập Google → nhấn "Create API key"
3. Copy key dán vào ô trong app

## Cài đặt & chạy

```bash
# 1. Tạo môi trường ảo
python3 -m venv venv
source venv/bin/activate      # macOS/Linux

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Chạy app
python3 app.py
```

Mở trình duyệt: http://localhost:7860

## Cách dùng

1. Dán Gemini API key vào ô đầu trang
2. Upload 1 hoặc nhiều PDF papers
3. Chọn chế độ phân tích
4. Nhấn gợi ý nhanh hoặc tự nhập câu hỏi
5. Xem biểu đồ + tín hiệu đầu tư bên phải

## Lần sau chạy lại

```bash
cd investment-analyzer
source venv/bin/activate
python3 app.py
```
