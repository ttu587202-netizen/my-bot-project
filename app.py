import os
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# --- Khởi tạo Client Gemini ---
# Ứng dụng Render của bạn phải có biến môi trường GENAI_API_KEY
try:
    API_KEY = os.environ.get("GENAI_API_KEY")
    if not API_KEY:
        raise ValueError("GENAI_API_KEY not found in environment variables.")
    
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"Lỗi khởi tạo Gemini Client: {e}")
    client = None

# --- Endpoint API Gemini ---
@app.route("/generate", methods=["POST"])
def generate_response():
    if not client:
        return jsonify({"error": "Dịch vụ AI chưa được cấu hình."}), 500
    
    try:
        data = request.json
        prompt = data.get("prompt", "Hãy nói cho tôi biết về lập trình Python.")
        
        # Gọi mô hình Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Mô hình nhanh và hiệu quả
            contents=prompt
        )
        
        return jsonify({
            "status": "success",
            "prompt": prompt,
            "ai_response": response.text
        })
    
    except Exception as e:
        return jsonify({"error": f"Lỗi trong quá trình gọi API Gemini: {str(e)}"}), 500

# --- Chạy ứng dụng ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
