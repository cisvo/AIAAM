Hướng dẫn chạy file code_EDA_thuc_te.py
Bước 1: Cài đặt Python (nếu chưa có)
Tải tại python.org/downloads → cài phiên bản 3.9 trở lên.
Khi cài nhớ tick vào "Add Python to PATH" trước khi nhấn Install.

Bước 2: Tạo thư mục và đặt file đúng chỗ
Tạo 1 thư mục trên máy, đặt tất cả vào đó:
📁 EDA_Project/
    ├── code_EDA_thuc_te.py
    ├── owid-covid-data.csv
    ├── marketing_campaign.csv
    ├── winequality-red.csv
    └── diabetes.csv
Quan trọng: 4 file CSV phải nằm cùng thư mục với file .py.

Bước 3: Cài thư viện
Mở Command Prompt (Windows) hoặc Terminal (Mac/Linux), chạy:
bashpip install numpy pandas scipy matplotlib seaborn
Chờ cài xong (khoảng 1–2 phút).

Bước 4: Chạy file Python
Trong Command Prompt/Terminal, di chuyển vào thư mục vừa tạo:
bash# Windows
cd C:\Users\TenBan\EDA_Project

# Mac/Linux
cd /Users/TenBan/EDA_Project
Sau đó chạy:
bashpython code_EDA_thuc_te.py

Bước 5: Kết quả
Sau khi chạy xong bạn sẽ thấy:

In ra terminal: Tất cả số liệu thống kê (mean, median, std...)
Tạo ra các file ảnh .png trong cùng thư mục (14 biểu đồ)


Lỗi thường gặp và cách xử lý
LỗiNguyên nhânCách xử lýModuleNotFoundError: No module named 'pandas'Chưa cài thư việnChạy lại lệnh pip ở Bước 3FileNotFoundError: winequality-red.csvFile CSV không đúng thư mụcKiểm tra lại 4 file CSV có cùng thư mục khôngpython không nhậnPython chưa vào PATHThử python3 thay vì python
