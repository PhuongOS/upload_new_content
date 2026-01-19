import os
from flask import Flask, send_from_directory
from flasgger import Swagger
from routes import api_bp

# Khởi tạo ứng dựng Flask
app = Flask(__name__, static_url_path='', static_folder='Fontend')
# Cấu hình Swagger để tự động tạo tài liệu API
swagger = Swagger(app)

# Đăng ký tập hợp các API từ file routes.py
app.register_blueprint(api_bp)

# --- PHỤC VỤ GIAO DIỆN NGƯỜI DÙNG (FRONTEND) ---

@app.route('/')
def root():
    """Trả về trang chủ index.html từ thư mục Fontend"""
    return send_from_directory('Fontend', 'index.html')

@app.route('/<path:path>')
def send_static(path):
    """Phục vụ các file tĩnh như CSS, JS, ảnh từ thư mục Fontend"""
    return send_from_directory('Fontend', path)

if __name__ == '__main__':
    # Lấy PORT từ môi trường hoặc mặc định là 3000
    run_port = int(os.environ.get("PORT", 3000))
    print(f"Backend Server đang chạy tại: http://localhost:{run_port}")
    # Chạy server (không bật debug để đảm bảo ổn định trong luồng thread)
    app.run(host='0.0.0.0', port=run_port, debug=False)
