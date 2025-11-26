import os
from flask import Flask, request, jsonify
from google import genai
from google.generativeai.errors import APIError
import logging

# Thiết lập logging cơ bản để dễ dàng gỡ lỗi trên Render
logging.basicConfig(level=logging.INFO)

# --- KHỞI TẠO ỨNG DỤNG ---
# Đảm bảo tên biến là 'app' để tương thích với lệnh gunicorn app:app
app = Flask(__name__)

# --- Cấu hình và Khởi tạo Gemini Client ---
API_KEY = os.environ.get("GENAI_API_KEY")
client = None

if API_KEY:
    try:
        # Khởi tạo client chỉ khi có API Key
        client = genai.Client(api_key=API_KEY)
        logging.info("Gemini Client được khởi tạo thành công.")
    except Exception as e:
        logging.error(f"CẢNH BÁO: Lỗi khởi tạo Gemini Client: {e}")
        client = None
else:
    logging.warning("CẢNH BÁO: Không tìm thấy biến môi trường GENAI_API_KEY. Lệnh Gemini sẽ không hoạt động.")


# --- 1. Endpoint Trạng thái (Health Check) ---
@app.route("/", methods=["GET"])
def health_check():
    """Endpoint để kiểm tra trạng thái bot online."""
    status = {
        "status": "online",
        "message": "Bot đang hoạt động.",
        "gemini_ready": client is not None
    }
    return jsonify(status)

# --- 2. Endpoint Hỏi Gemini ---
@app.route("/ask_gemini", methods=["POST"])
def ask_gemini():
    """Endpoint để gửi câu hỏi và nhận câu trả lời từ Gemini."""
    
    if not client:
        return jsonify({
            "error": "Lỗi cấu hình",
            "message": "Không tìm thấy API Key hoặc lỗi khởi tạo Gemini. Hãy kiểm tra biến môi trường GENAI_API_KEY trên Render."
        }), 500

    try:
        data = request.get_json()
        prompt = data.get("prompt")
        
        if not prompt:
            return jsonify({"error": "Thiếu tham số", "message": "Vui lòng cung cấp 'prompt' trong body JSON."}), 400
        
        logging.info(f"Đang hỏi Gemini với prompt: {prompt[:50]}...")
        
        # Gọi mô hình Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Mô hình nhanh và hiệu quả
            contents=prompt
        )
        
        return jsonify({
            "status": "success",
            "prompt_sent": prompt,
            "gemini_response": response.text
        })
    
    except APIError as e:
        logging.error(f"Lỗi API Gemini: {str(e)}")
        return jsonify({
            "error": "Lỗi API Gemini",
            "message": f"Đã xảy ra lỗi khi gọi API Gemini: {str(e)}. Hãy kiểm tra lại API Key hoặc giới hạn sử dụng."
        }), 503
        
    except Exception as e:
        logging.error(f"Lỗi không xác định: {str(e)}")
        return jsonify({"error": "Lỗi không xác định", "message": str(e)}), 500

# --- Lệnh chạy ứng dụng (Chỉ chạy khi kiểm thử cục bộ) ---
# Render sẽ dùng gunicorn, nên phần này không chạy trên Render
if __name__ == '__main__':
    # Chỉ chạy cục bộ cho mục đích kiểm thử
    app.run(host='0.0.0.0', port=5000)
        
