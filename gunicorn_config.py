import os

# Lấy cổng từ biến môi trường của Render, mặc định là 8000
port = os.environ.get('PORT', '8000')

# Địa chỉ lắng nghe
bind = f"0.0.0.0:{port}"

# Số lượng worker (Thường là 2x CPU + 1, nhưng 4 là an toàn trên Render)
workers = 4

# Số lượng thread (Nếu không đặt, mặc định là 1)
threads = 2

# Thời gian chờ (timeout) cho worker (tính bằng giây)
timeout = 120

# Tên file ứng dụng Flask: 'app' là tên file, 'app' là tên biến Flask
wsgi_app = "app:app"
