# Cần cài đặt: pip install discord.py requests flask
import discord
from discord.ext import commands
import requests
from requests.exceptions import Timeout, HTTPError
import uuid
import random
from datetime import datetime
import os 
import threading 
from flask import Flask 
import time

# ==========================================================
# >>> CẤU HÌNH BOT & KHÓA <<<
# ==========================================================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
PORT = int(os.environ.get("PORT", 10000)) 
# ==========================================================

# >>> CƠ CHẾ TỰ KHỞI ĐỘNG LẠI (5 TIẾNG) ĐÃ BỊ XÓA BỎ HOÀN TOÀN <<<

# --- 1. Thiết lập Cấu hình API, Lưu trữ và Bảng Màu Thống nhất ---

API_BASE_URL = "https://api.mail.tm"
DEFAULT_TIMEOUT = 15
RENDER_URL = "https://my-bot-project-44vv.onrender.com" # URL CỦA BẠN ĐÃ ĐƯỢC CẬP NHẬT

# Bảng Màu Siêu Hiện Đại (Hyper-Aesthetic)
VIBRANT_COLOR = 0x30D5C8      
ACCENT_COLOR = 0xFF5733       
ERROR_COLOR = 0xED4245        
WARNING_COLOR = 0xFEE75C      
SUCCESS_COLOR = 0x57F287      
NEUTRAL_COLOR = 0x2F3136      

# Key: Discord User ID (int), Value: {'address': str, 'token': str, 'account_id': str}
user_temp_mails = {}

# Danh sách các domain bị cấm hoặc không mong muốn
DOMAIN_BLACKLIST = ["example.com", "youdontwantme.net"] 

# Hệ thống AI Giám sát
user_ai_monitor = {} 

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix=None, intents=intents, help_command=None) 

# ==========================================================
# >>> 2. LỚP GIÁM SÁT AI (AI Monitoring System) V9.0 <<<
# ==========================================================
class AIAntiAbuseMonitor:
    """Giả lập hệ thống AI bảo vệ và giám sát người chơi thời gian thực."""
    
    ABUSE_THRESHOLD = 5         
    MAX_EMAIL_PER_HOUR = 10     

    def __init__(self, user_id):
        self.user_id = user_id
        self.abuse_score = 0
        self.last_email_creation_time = time.time()
        self.email_count_last_hour = 0
        self.banned_until = 0
        
        self.cooldown_duration = 0      
        self.cooldown_start_time = 0    

    def check_and_update_creation(self):
        current_time = time.time()

        if current_time - self.last_email_creation_time > 3600:
            self.email_count_last_hour = 0
            self.last_email_creation_time = current_time

        self.email_count_last_hour += 1

        if self.email_count_last_hour > self.MAX_EMAIL_PER_HOUR:
            self.abuse_score += 2
            
        if self.abuse_score >= self.ABUSE_THRESHOLD:
            self.banned_until = current_time + 3600  
            return False, "🛑 AI V9.0: Cấm truy cập 1 giờ do lạm dụng tần suất tạo mail quá mức."

        return True, None

    def check_ban_status(self):
        current_time = time.time()
        if self.banned_until > current_time:
            time_left = self.banned_until - current_time
            return False, f"🛑 HỆ THỐNG AI ĐÃ CHẶN: Bạn bị cấm truy cập bot. Vui lòng chờ {int(time_left // 60)} phút {int(time_left % 60)} giây."
        
        if self.abuse_score > 0:
            self.abuse_score -= 1 
            
        return True, None
# ==========================================================


# --- 3. Hàm Tiện Ích ---

def create_styled_embed(title, description, color, fields=None, footer_text=None):
    """Hàm tiện ích tạo Embed với style hiện đại."""
    title = title[:256] 
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    if fields:
        for name, value, inline in fields:
            name = str(name)[:256] if name else "Không tên"
            value = str(value)[:1024] if value else "Không nội dung"
            embed.add_field(name=name, value=value, inline=inline)
            
    if footer_text:
        footer_text = str(footer_text)[:2048]
        for line in footer_text.split('\n'):
            embed.set_footer(text=line)
            break 
            
    return embed

def get_user_monitor(user_id):
    if user_id not in user_ai_monitor:
        user_ai_monitor[user_id] = AIAntiAbuseMonitor(user_id)
    return user_ai_monitor[user_id]

def format_time_duration(seconds):
    if seconds < 1:
        return "1 giây"
    
    seconds = int(seconds)
    minutes = seconds // 60
    secs = seconds % 60
    
    if minutes > 0:
        return f"{minutes} phút {secs} giây"
    return f"{secs} giây"

async def check_mail_logic(user_id: int):
    """Logic kiểm tra mail, xem 5 thư gần nhất."""
    
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
                "💌 HỘP THƯ TRỐNG RỖNG",
                f"✅ Địa chỉ đang hoạt động: **`{email_address}`**\n\n**Trạng thái:** Không tìm thấy tin nhắn nào. Nhấn **Làm Mới Mailbox** để kiểm tra lại.",
                VIBRANT_COLOR
            )
            embed.set_footer(text=f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
            return embed

        total_messages = len(messages)
        display_count = min(total_messages, 5)
        
        embed = create_styled_embed(
            f"📬 HỘP THƯ ĐẾN ({total_messages} Thư) - Hiển thị {display_count} thư gần nhất",
            f"Địa chỉ Email của bạn: **`{email_address}`**",
            VIBRANT_COLOR,
        )

        for i, msg in enumerate(messages[:5]): 
            detail_response = requests.get(f"{API_BASE_URL}/messages/{msg['id']}", headers=headers, timeout=DEFAULT_TIMEOUT)
            
            sender = msg.get('from', {}).get('address', 'Ẩn danh')
            subject = msg.get('subject', 'Không có tiêu đề')
            
            if detail_response.status_code == 200:
                detail = detail_response.json()
                body_text = detail.get('text', 'Không có nội dung văn bản.')
                
                content_preview = body_text.strip()[:150].replace('\n', ' ')
                if len(body_text.strip()) > 150:
                    content_preview += '...'
                
                embed_fields.append((
                    f"#{i+1} | Chủ đề: **{subject}**", 
                    f"**👤 Người gửi:** `{sender}`\n**📝 Xem trước:** `{content_preview}`",
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
        print(f"Lỗi Xử Lý Dữ Liệu: {e}")
        return create_styled_embed("❌ Lỗi Xử Lý Dữ Liệu", f"Đã xảy ra lỗi không xác định: `{e}`. Vui lòng thử lại.", ERROR_COLOR)


# --- 4. Custom Views (Buttons Rendering) ---

class CheckMailView(discord.ui.View):
    """View chứa nút Tương tác cho email ảo (Làm Mới)."""
    def __init__(self, user_id: int):
        super().__init__(timeout=300) 
        self.user_id = user_id

    @discord.ui.button(label="Làm Mới Mailbox", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Bạn không có quyền tương tác với mail của người khác.", ephemeral=True)
            return

        await interaction.response.edit_message(
            embed=create_styled_embed("🔄 Đang Làm Mới Mail...", "Vui lòng chờ trong giây lát. Hệ thống đang kiểm tra hộp thư...", VIBRANT_COLOR),
            view=self
        )

        result_embed = await check_mail_logic(self.user_id) 
        
        await interaction.edit_original_response(embed=result_embed, view=self)

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

        await interaction.response.defer(thinking=True, ephemeral=True) 
        
        result_embed = await check_mail_logic(self.user_id)
        
        await interaction.followup.send(embed=result_embed, view=CheckMailView(self.user_id), ephemeral=True)


# --- 5. Các Lệnh Slash ---

@bot.tree.command(name="get_email", description="Tạo một địa chỉ email ảo tạm thời mới (Mail.tm).")
async def get_temp_email(interaction: discord.Interaction):
    
    user_id = interaction.user.id
    monitor = get_user_monitor(user_id)
    
    current_time = time.time()
    
    # ********** 5.1 KIỂM TRA COOLDOWN NGẪU NHIÊN **********
    time_elapsed = current_time - monitor.cooldown_start_time
    
    if time_elapsed < monitor.cooldown_duration:
        remaining = monitor.cooldown_duration - time_elapsed
        
        time_left_str = format_time_duration(remaining)
        total_cooldown_str = format_time_duration(monitor.cooldown_duration)
        
        embed = create_styled_embed(
            "⏳ ĐANG TRÊN COOLDOWN NGẪU NHIÊN",
            f"Bạn đang trong thời gian chờ **{total_cooldown_str}** ngẫu nhiên được gán.\nVui lòng chờ **{time_left_str}** trước khi tạo email tiếp theo.",
            WARNING_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    
    # ********** 5.2 KIỂM TRA BAN CỦA HỆ THỐNG GIÁM SÁT **********
    is_safe, ban_message = monitor.check_ban_status()
    
    if not is_safe:
        await interaction.response.send_message(embed=create_styled_embed("🚫 AI BLOCK", ban_message, ERROR_COLOR), ephemeral=True)
        return
    
    is_safe, ban_message = monitor.check_and_update_creation()
    if not is_safe:
        await interaction.response.send_message(embed=create_styled_embed("🚫 AI BLOCK", ban_message, ERROR_COLOR), ephemeral=True)
        return
    # ********** KẾT THÚC BƯỚC ẢI AI **********
    
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    try:
        # Logic tạo tài khoản
        domains_response = requests.get(f"{API_BASE_URL}/domains", timeout=DEFAULT_TIMEOUT)
        domains_response.raise_for_status() 

        domain_list = domains_response.json().get('hydra:member', [])
        if not domain_list:
            raise Exception("Không thể lấy danh sách domain hợp lệ.")
            
        valid_domains = [d['domain'] for d in domain_list if d['domain'] not in DOMAIN_BLACKLIST]
        
        if not valid_domains:
            await interaction.followup.send(
                embed=create_styled_embed("🛑 Lỗi Hệ Thống Domain", "Không còn domain khả dụng (tất cả đã bị cấm).", ERROR_COLOR), 
                ephemeral=True
            )
            return
            
        domain = random.choice(valid_domains)
        
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
        
        
        # ********** 5.3 ÁP DỤNG COOLDOWN NGẪU NHIÊN MỚI **********
        new_cooldown = random.randint(30, 300) 
        
        monitor.cooldown_duration = new_cooldown
        monitor.cooldown_start_time = time.time()
        
        new_cooldown_str = format_time_duration(new_cooldown)
        # ********** KẾT THÚC ÁP DỤNG COOLDOWN **********

        
        # Render Embed
        embed = create_styled_embed(
            "⚡️ TẠO EMAIL ẢO THÀNH CÔNG (MAIL.TM)",
            "🎉 Địa chỉ email tạm thời của bạn đã sẵn sàng. Email cũ đã được thay thế. **LƯU Ý: Email sẽ tự động hết hạn sau 30 phút - 2 giờ.**", 
            ACCENT_COLOR, 
            fields=[
                ("📧 Địa Chỉ Email", f"```\n{email_address}```", False), 
                ("🌐 Nền Tảng", "Mail.tm", True),
                ("⏱️ Thời Hạn", "Tự động hết hạn", True)
            ],
            footer_text=f"Cooldown ngẫu nhiên tiếp theo: {new_cooldown_str}\n© Hyper-Aesthetic System | AI Monitoring System V9.0 Active - Permanent Run"
        )

        await interaction.followup.send(embed=embed, view=EmailCreationView(user_id), ephemeral=True)

    except Timeout:
        await interaction.followup.send(embed=create_styled_embed("🛑 Lỗi Kết Nối API", "Mail.tm không phản hồi kịp thời (Timeout).", ERROR_COLOR), ephemeral=True)
    except HTTPError as e:
        await interaction.followup.send(embed=create_styled_embed("🛑 Lỗi API Mail.tm", f"Không thể tạo tài khoản. Mã lỗi: {e.response.status_code}.", ERROR_COLOR), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=create_styled_embed("❌ Lỗi Hệ Thống", f"Đã xảy ra lỗi không xác định: `{e}`", ERROR_COLOR), ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if not interaction.response.is_done():
        await interaction.response.send_message(
            embed=create_styled_embed("❌ Lỗi Hệ Thống Chung", f"Đã xảy ra lỗi không xác định: `{error}`", ERROR_COLOR),
            ephemeral=True
        )


@bot.tree.command(name="check_mail", description="Kiểm tra hộp thư email ảo gần nhất của bạn.")
async def check_temp_mail(interaction: discord.Interaction):
    user_id = interaction.user.id
    monitor = get_user_monitor(user_id)
    
    # Kiểm tra Ban AI
    is_safe, ban_message = monitor.check_ban_status()
    if not is_safe:
        await interaction.response.send_message(embed=create_styled_embed("🚫 AI BLOCK", ban_message, ERROR_COLOR), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    result_embed = await check_mail_logic(user_id) 
    
    if user_id in user_temp_mails:
        await interaction.followup.send(embed=result_embed, view=CheckMailView(user_id), ephemeral=True)
    else:
        await interaction.followup.send(embed=result_embed, ephemeral=True)


@bot.tree.command(name="help", description="Hiển thị bảng lệnh Siêu Hiện Đại.")
async def help_command(interaction: discord.Interaction):
    
    embed = create_styled_embed(
        "🌐  HYPER-MAIL: DỊCH VỤ EMAIL ẢO V9.0 (PERMANENT RUN)",
        "Bot đã được tối ưu hóa để chạy **liên tục 24/24** bằng cách sử dụng UptimeRobot.",
        VIBRANT_COLOR, 
        fields=[
            ("⚡️ Lệnh Chính: /get_email", "Tạo một địa chỉ email tạm thời mới.", False),
            (
                "Mô Tả", 
                "Thời gian chờ giữa các lần dùng là **ngẫu nhiên** từ **30 giây đến 5 phút**. Tối đa 10 mail/giờ.", 
                True
            ),
            ("📥 Lệnh Kiểm Tra: /check_mail", "Xem và làm mới hộp thư đến của email gần nhất của bạn.", False),
            (
                "Mô Tả", 
                "Kiểm tra thủ công (**5 thư gần nhất**) của email hiện tại.", 
                True
            ),
            ("🔄 Cấu hình 24/24 (UptimeRobot)", "Đảm bảo bot luôn hoạt động.", False),
            (
                "Ghi Chú", 
                f"Để bot chạy liên tục, bạn cần thiết lập UptimeRobot để ping địa chỉ này:\n**`{RENDER_URL}`**", 
                True
            )
        ],
        footer_text="© Hyper-Aesthetic System | AI Monitoring System V9.0 Active - Permanent Run"
    )

    await interaction.response.send_message(embed=embed, ephemeral=False)

# --- 6. FIX RENDER: Thiết lập Web Server Flask ---

app = Flask(__name__)

@app.route('/')
def home():
    """Endpoint cơ bản để Render kiểm tra bot còn hoạt động không."""
    return "Bot Discord Email Ảo V9.0 đang hoạt động (Permanent Run)!", 200

def run_flask():
    """Chạy Flask server trên thread riêng."""
    app.run(host="0.0.0.0", port=PORT)

# --- 7. Sự kiện và Khởi động Bot Chính ---

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
        print("LỖI: Biến môi trường DISCORD_TOKEN chưa được thiết lập.")
        return
        
    # Chạy Flask server trên một thread riêng (QUAN TRỌNG: để nhận Ping từ UptimeRobot)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Bot sẽ chạy liên tục, chỉ khởi động lại khi có sự cố hệ thống (Render/Code Crash).

    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("LỖI: Discord Bot Token không hợp lệ.")
    except Exception as e:
        print(f"Lỗi xảy ra khi chạy bot: {e}")

if __name__ == '__main__':
    main()
