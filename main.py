# Cần cài đặt: pip install discord.py requests flask
import discord
from discord.ext import commands
import requests
from requests.exceptions import Timeout, HTTPError
import uuid
import random
from datetime import datetime
import os 
import threading # Cần thiết để chạy bot và web server song song
from flask import Flask # Import Flask

# ==========================================================
# >>> CẤU HÌNH BOT & KHÓA <<<
# ==========================================================
# Lấy Discord Token từ Biến Môi Trường (RENDER)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
# PORT mặc định Render sẽ cấp phát
PORT = int(os.environ.get("PORT", 10000)) 
# ==========================================================

# --- 1. Thiết lập Cấu hình API, Lưu trữ và Bảng Màu Thống nhất ---

API_BASE_URL = "https://api.mail.tm"
DEFAULT_TIMEOUT = 15

# Bảng Màu Hiện Đại (HEX)
VIBRANT_COLOR = 0x30D5C8  # Neon Cyan
ERROR_COLOR = 0xED4245    # Discord Red
WARNING_COLOR = 0xFEE75C  # Discord Yellow
SUCCESS_COLOR = 0x57F287  # Discord Green

# Key: Discord User ID (int), Value: {'address': str, 'token': str, 'account_id': str}
user_temp_mails = {}

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix=None, intents=intents, help_command=None) 

# --- 2. Hàm Tiện Ích ---

def create_styled_embed(title, description, color, thumbnail_url=None, fields=None):
    """Hàm tiện ích tạo Embed với style hiện đại."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    return embed

async def delete_email_account_logic(user_id: int):
    """Logic xóa tài khoản email, trả về Embed."""
    if user_id not in user_temp_mails:
        return create_styled_embed(
            "⚠️ Không tìm thấy Email", 
            "Bạn không có email ảo đang hoạt động để xóa.", 
            WARNING_COLOR
        )
        
    email_info = user_temp_mails[user_id]
    account_id = email_info['account_id']
    email_token = email_info['token']
    email_address = email_info['address']
    
    try:
        headers = {'Authorization': f'Bearer {email_token}'}
        delete_response = requests.delete(f"{API_BASE_URL}/accounts/{account_id}", headers=headers, timeout=DEFAULT_TIMEOUT)
        
        # Xóa khỏi bộ nhớ cục bộ
        del user_temp_mails[user_id]

        if delete_response.status_code == 204:
            return create_styled_embed(
                "🗑️ ĐÃ XÓA THÀNH CÔNG",
                f"Địa chỉ **`{email_address}`** đã được gỡ bỏ vĩnh viễn khỏi hệ thống Mail.tm.",
                VIBRANT_COLOR,
                thumbnail_url="https://i.imgur.com/8QzXy2A.png"
            )
        else:
             return create_styled_embed(
                "🛑 Lỗi Xóa API", 
                f"Xóa mail thất bại (Mã lỗi: {delete_response.status_code}). Tuy nhiên, email đã bị xóa khỏi bộ nhớ bot.", 
                ERROR_COLOR
            )

    except Exception as e:
        if user_id in user_temp_mails:
            del user_temp_mails[user_id]
        
        return create_styled_embed(
            "❌ Lỗi Hệ Thống", 
            f"Lỗi kết nối khi xóa: `{e}`. Email đã bị xóa khỏi bot.",
            ERROR_COLOR
        )

async def check_mail_logic(user_id: int):
    """Logic kiểm tra mail được tách ra để tái sử dụng."""
    
    if user_id not in user_temp_mails:
        return create_styled_embed(
            "⚠️ Chưa Có Email", 
            "Bạn chưa có email ảo. Vui lòng sử dụng `/get_email` trước.", 
            WARNING_COLOR
        )

    email_info = user_temp_mails[user_id]
    email_token = email_info['token']
    email_address = email_info['address']

    try:
        headers = {'Authorization': f'Bearer {email_token}'}
        messages_response = requests.get(f"{API_BASE_URL}/messages", headers=headers, timeout=DEFAULT_TIMEOUT)
        messages_response.raise_for_status() 

        messages_data = messages_response.json()
        messages = messages_data.get('hydra:member', [])
        
        embed_fields = []

        if not messages:
            embed = create_styled_embed(
                "📥 HỘP THƯ TRỐNG",
                f"Địa chỉ đang kiểm tra: **`{email_address}`**\n\nChưa có tin nhắn nào. Vẫn đang chờ tin...",
                VIBRANT_COLOR
            )
            embed.set_footer(text=f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
            return embed

        # Tạo Embed hiển thị các tin nhắn
        embed = create_styled_embed(
            f"📬 {len(messages)} TIN NHẮN MỚI NHẤT",
            f"Địa chỉ đang kiểm tra: **`{email_address}`**",
            VIBRANT_COLOR,
            thumbnail_url="https://i.imgur.com/L79tK0k.png" 
        )

        # Chỉ hiển thị 3 tin nhắn mới nhất để tránh Embed quá dài
        for i, msg in enumerate(messages[:3]): 
            detail_response = requests.get(f"{API_BASE_URL}/messages/{msg['id']}", headers=headers, timeout=DEFAULT_TIMEOUT)
            
            sender = msg.get('from', {}).get('address', 'Ẩn danh')
            subject = msg.get('subject', 'Không có tiêu đề')
            
            if detail_response.status_code == 200:
                detail = detail_response.json()
                body_text = detail.get('text', 'Không có nội dung văn bản.')
                
                content_preview = body_text.strip()[:200].replace('\n', ' ')
                
                embed_fields.append((
                    f"📧 Tiêu đề: {subject}",
                    f"**Người gửi:** `{sender}`\n**Xem trước:** ```\n{content_preview}\n```",
                    False
                ))
            else:
                 embed_fields.append((
                    f"❌ #{i+1}: Lỗi tải chi tiết",
                    f"Không thể tải nội dung chi tiết (Mã lỗi: {detail_response.status_code}).",
                    False
                ))
        
        for name, value, inline in embed_fields:
            embed.add_field(name=name, value=value, inline=inline)

        embed.set_footer(text=f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
        return embed

    except Timeout:
        return create_styled_embed("🛑 Lỗi Kết Nối API", "Mail.tm không phản hồi kịp thời (Timeout).", ERROR_COLOR)
    except HTTPError as e:
        return create_styled_embed("🛑 Lỗi Phản Hồi API", f"API Mail.tm lỗi HTTP: {e.response.status_code}. Token có thể hết hạn.", ERROR_COLOR)
    except Exception as e:
        return create_styled_embed("❌ Lỗi Xử Lý Dữ Liệu", f"Đã xảy ra lỗi không xác định: `{e}`. Vui lòng thử lại.", ERROR_COLOR)


# --- 3. Custom Views (Buttons Rendering) ---

class CheckMailView(discord.ui.View):
    """View chứa các nút tương tác cho email ảo (Kiểm tra & Xóa)."""
    def __init__(self, user_id: int):
        super().__init__(timeout=300) 
        self.user_id = user_id

    # Tối ưu hóa RENDER: EDIT MESSAGE cho tương tác nút
    @discord.ui.button(label="🔄 Kiểm tra lại Hộp thư", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không có quyền tương tác với mail của người khác.", ephemeral=True)
            return

        # BƯỚC 1: Render ngay lập tức (EDIT) trạng thái loading
        await interaction.response.edit_message(
            embed=create_styled_embed("🔄 Đang Render...", "Vui lòng chờ. Hệ thống đang lấy dữ liệu mới nhất...", VIBRANT_COLOR),
            view=self
        )
        
        # BƯỚC 2: Gọi API (tốn thời gian)
        result_embed = await check_mail_logic(self.user_id)
        
        # BƯỚC 3: Render kết quả cuối cùng
        await interaction.edit_original_response(embed=result_embed, view=self)

    @discord.ui.button(label="🗑️ Xóa Email Vĩnh Viễn", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không có quyền tương tác với mail của người khác.", ephemeral=True)
            return
            
        # BƯỚC 1: Render ngay lập tức trạng thái đang xóa
        await interaction.response.edit_message(
            embed=create_styled_embed("🗑️ Đang Xóa...", "Vui lòng chờ. Hệ thống đang gỡ bỏ tài khoản Mail.tm.", ERROR_COLOR),
            view=None
        )
        
        # BƯỚC 2: Gọi Logic xóa
        result_embed = await delete_email_account_logic(self.user_id)
        
        # BƯỚC 3: Render kết quả cuối cùng (View=None vì đã xóa)
        await interaction.edit_original_response(embed=result_embed, view=None)

class EmailCreationView(discord.ui.View):
    """View gắn vào tin nhắn tạo email, chỉ có nút Kiểm tra Mail."""
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    @discord.ui.button(label="📥 Kiểm tra Hộp Thư Ngay!", style=discord.ButtonStyle.success, emoji="✅")
    async def check_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không có quyền tương tác với mail của người khác.", ephemeral=True)
            return

        # Dùng defer cho lệnh chuyển trạng thái và chuẩn bị gửi tin nhắn mới (followup)
        await interaction.response.defer(thinking=True, ephemeral=True) 
        
        result_embed = await check_mail_logic(self.user_id)
        
        # Gửi tin nhắn mới (followup) với View kiểm tra mail
        await interaction.followup.send(embed=result_embed, view=CheckMailView(self.user_id), ephemeral=True)

# --- 4. Các Lệnh Slash (Tương tác ban đầu) ---

@bot.tree.command(name="get_email", description="Tạo một địa chỉ email ảo tạm thời mới (Mail.tm).")
async def get_temp_email(interaction: discord.Interaction):
    
    user_id = interaction.user.id
    # Dùng defer cho lệnh tạo tài khoản (tốn thời gian)
    await interaction.response.defer(ephemeral=True, thinking=True)

    if user_id in user_temp_mails:
        email_info = user_temp_mails[user_id]
        embed = create_styled_embed(
            "⚠️ EMAIL ĐANG HOẠT ĐỘNG",
            f"Bạn đã có một email: **`{email_info['address']}`**. Vui lòng xóa nó bằng `/delete_email` trước.",
            WARNING_COLOR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    try:
        # Logic tạo tài khoản
        domains_response = requests.get(f"{API_BASE_URL}/domains", timeout=DEFAULT_TIMEOUT)
        domains_response.raise_for_status() 

        domain_list = domains_response.json().get('hydra:member', [])
        if not domain_list:
            raise Exception("Không thể lấy danh sách domain hợp lệ.")
            
        domain = random.choice(domain_list)['domain']
        
        username = uuid.uuid4().hex[:10]
        password = uuid.uuid4().hex
        email_address = f"{username}@{domain}"
        
        account_data = {"address": email_address, "password": password}
        create_response = requests.post(f"{API_BASE_URL}/accounts", json=account_data, timeout=DEFAULT_TIMEOUT)
        create_response.raise_for_status()
        account_id = create_response.json()['id']
        
        login_data = {"address": email_address, "password": password}
        login_response = requests.post(f"{API_BASE_URL}/token", json=login_data, timeout=DEFAULT_TIMEOUT)
        login_response.raise_for_status()
        token = login_response.json()['token']
        
        user_temp_mails[user_id] = {'address': email_address, 'token': token, 'account_id': account_id}
        
        # Render kết quả
        embed = create_styled_embed(
            "⚡️ TẠO EMAIL ẢO THÀNH CÔNG (MAIL.TM)",
            "🎉 Địa chỉ email tạm thời của bạn đã sẵn sàng để nhận tin.",
            VIBRANT_COLOR,
            thumbnail_url="https://i.imgur.com/8QzXy2A.png", 
            fields=[
                ("📧 Địa Chỉ Email", f"```\n{email_address}\n```", False),
                ("🌐 Nền Tảng", "Mail.tm", True),
                ("⏱️ Thời Hạn", "Đến khi bạn xóa", True)
            ]
        )
        embed.set_footer(text=f"Tạo bởi {interaction.user.name} | Click nút để kiểm tra!")

        await interaction.followup.send(embed=embed, view=EmailCreationView(user_id), ephemeral=True)

    except Timeout:
        await interaction.followup.send(embed=create_styled_embed("🛑 Lỗi Kết Nối API", "Mail.tm không phản hồi kịp thời (Timeout).", ERROR_COLOR), ephemeral=True)
    except HTTPError as e:
        await interaction.followup.send(embed=create_styled_embed("🛑 Lỗi API Mail.tm", f"Không thể tạo tài khoản. Mã lỗi: {e.response.status_code}.", ERROR_COLOR), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=create_styled_embed("❌ Lỗi Hệ Thống", f"Đã xảy ra lỗi không xác định: `{e}`", ERROR_COLOR), ephemeral=True)

@bot.tree.command(name="check_mail", description="Kiểm tra hộp thư email ảo hiện tại của bạn.")
async def check_temp_mail(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    result_embed = await check_mail_logic(user_id)
    
    if user_id in user_temp_mails:
        await interaction.followup.send(embed=result_embed, view=CheckMailView(user_id), ephemeral=True)
    else:
        await interaction.followup.send(embed=result_embed, ephemeral=True)


@bot.tree.command(name="delete_email", description="Xóa email ảo đang hoạt động của bạn.")
async def delete_temp_email(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    result_embed = await delete_email_account_logic(user_id)
    
    await interaction.followup.send(embed=result_embed, ephemeral=True)

# --- 5. FIX RENDER: Thiết lập Web Server Flask ---

app = Flask(__name__)

@app.route('/')
def home():
    """Endpoint cơ bản để Render kiểm tra bot còn hoạt động không."""
    return "Bot Discord Email Ảo đang hoạt động!", 200

def run_flask():
    """Chạy Flask server trên thread riêng."""
    # Render yêu cầu host 0.0.0.0 để nghe tất cả các giao diện mạng
    app.run(host="0.0.0.0", port=PORT)

# --- 6. Sự kiện và Khởi động Bot Chính ---

@bot.event
async def on_ready():
    """Thông báo khi bot đã sẵn sàng và đồng bộ lệnh slash."""
    print('---' * 15)
    print(f'🤖 Bot đã đăng nhập với tên: {bot.user}')
    print('Bắt đầu đồng bộ hóa lệnh slash...')
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã đồng bộ hóa {len(synced)} lệnh slash.")
    except Exception as e:
        print(f"❌ Lỗi khi đồng bộ hóa lệnh slash: {e}")
        
    print(f'Bot sẵn sàng nhận lệnh email ảo. Flask chạy trên cổng {PORT}')
    print('---' * 15)

def main():
    if not DISCORD_TOKEN:
        print("LỖI: Biến môi trường DISCORD_TOKEN chưa được thiết lập. Vui lòng thiết lập DISCORD_TOKEN trên Render.")
        return
        
    # Chạy Flask server trên một thread riêng (tránh block bot)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    try:
        # Chạy Bot chính
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("LỖI: Discord Bot Token không hợp lệ. Kiểm tra giá trị DISCORD_TOKEN.")
    except Exception as e:
        print(f"Lỗi xảy ra khi chạy bot: {e}")

if __name__ == '__main__':
    main()
        
