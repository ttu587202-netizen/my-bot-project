import os
from flask import Flask, request, jsonify
from google import genai 
from google.genai.errors import APIError 
import logging

logging.basicConfig(level=logging.INFO)

# --- KHỞI TẠO ỨNG DỤNG ---
app = Flask(__name__)

# --- Cấu hình và Khởi tạo Gemini Client ---
API_KEY = os.environ.get("GENAI_API_KEY")
client = None

if API_KEY:
    try:
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
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
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

# Phần này không chạy trên Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
            
