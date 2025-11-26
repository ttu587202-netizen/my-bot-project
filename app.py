import os
from flask import Flask, request, jsonify
from google import genai
from google.generativeai.errors import APIError

app = Flask(__name__)

# --- Cấu hình và Khởi tạo Gemini Client ---
# Đảm bảo GENAI_API_KEY được thiết lập trong biến môi trường của Render
API_KEY = os.environ.get("GENAI_API_KEY")
client = None

if API_KEY:
    try:
        # Khởi tạo client chỉ khi có API Key
        client = genai.Client(api_key=API_KEY)
        print("Gemini Client được khởi tạo thành công.")
    except Exception as e:
        print(f"CẢNH BÁO: Lỗi khởi tạo Gemini Client: {e}")
        client = None
else:
    print("CẢNH BÁO: Không tìm thấy biến môi trường GENAI_API_KEY. Lệnh Gemini sẽ không hoạt động.")


# --- 1. Endpoint Trạng thái (Online Bot Check) ---
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
    
    # Kiểm tra xem client đã được khởi tạo thành công chưa
    if not client:
        return jsonify({
            "error": "Lỗi cấu hình",
            "message": "Không tìm thấy API Key hoặc lỗi khởi tạo Gemini. Hãy kiểm tra biến môi trường GENAI_API_KEY trên Render."
        }), 500

    try:
        data = request.json
        prompt = data.get("prompt")
        
        if not prompt:
            return jsonify({"error": "Thiếu tham số", "message": "Vui lòng cung cấp 'prompt' trong body JSON."}), 400
        
        # Gọi mô hình Gemini
        print(f"Đang hỏi Gemini với prompt: {prompt[:50]}...")
        
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
        # Xử lý các lỗi từ API của Google (ví dụ: API Key không hợp lệ, lỗi giới hạn)
        return jsonify({
            "error": "Lỗi API Gemini",
            "message": f"Đã xảy ra lỗi khi gọi API Gemini: {str(e)}"
        }), 503
        
    except Exception as e:
        return jsonify({"error": "Lỗi không xác định", "message": str(e)}), 500

# --- Chạy ứng dụng ---
if __name__ == '__main__':
    # Trong môi trường phát triển cục bộ, bạn có thể chạy:
    # app.run(host='0.0.0.0', port=5000, debug=True)
    # Trên Render, gunicorn sẽ chạy ứng dụng này
    pass
