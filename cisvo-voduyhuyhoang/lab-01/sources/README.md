# Hướng dẫn chạy file code_EDA_thuc_te.py

### Bước 1: Cài đặt Python (nếu chưa có)
* Tải tại [python.org/downloads](https://www.python.org/downloads) → cài phiên bản 3.9 trở lên.
* Khi cài nhớ tick vào **"Add Python to PATH"** trước khi nhấn Install.

### Bước 2: Tạo thư mục và đặt file đúng chỗ
Tạo 1 thư mục trên máy, đặt tất cả vào đó:

```
📁 EDA_Project/
├── code_EDA_thuc_te.py
├── owid-covid-data.csv
├── marketing_campaign.csv
├── winequality-red.csv
└── diabetes.csv
```

### Bước 3: Cài thư viện
Mở Command Prompt (Windows) hoặc Terminal (Mac/Linux), chạy:
```pip install numpy pandas scipy matplotlib seaborn```

### Bước 4: Chạy file Python
Trong Command Prompt/Terminal, di chuyển vào thư mục vừa tạo:
```
# Windows
cd C:\Users\TenBan\EDA_Project

# Mac/Linux
cd /Users/TenBan/EDA_Project
```

Sau đó chạy:
``` python code_EDA_thuc_te.py ```

### Bước 5: Kết quả
Sau khi chạy xong bạn sẽ thấy:

In ra terminal: Tất cả số liệu thống kê (mean, median, std...)
Tạo ra các file ảnh .png: trong cùng thư mục (14 biểu đồ)

### Lỗi thường gặp và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'pandas'` | Chưa cài thư viện | Chạy lại lệnh `pip` ở Bước 3 |
| `FileNotFoundError: winequality-red.csv` | File CSV không đúng thư mục | Kiểm tra lại 4 file CSV có cùng thư mục không |
| `python` không nhận | Python chưa vào PATH | Thử `python3` thay vì `python` |
