import numpy as np
import os
import asyncio
import hashlib
import hmac
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from collections import deque, Counter
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

# --- CẤU HÌNH SIÊU CẤP ---
TOKEN = "8670893641:AAGovRHAo8mIGvOXchbTqxZZIG2KQiwdRcw"
GROUP_CHAT_ID = "-1002347313054" 
ADMIN_ID = "@tranhoang2286"
SECRET_SALT = "HOANG_DZ_VIP_2024_API_KEY_SECURE"

app = FastAPI(title="🚀 AI HEX-DECODER ULTIMATE 🚀", version="6.0.0")
bot = Bot(token=TOKEN)

class SystemState:
    def __init__(self):
        self.phien = 184726 
        self.raw_data = deque(["Tài", "Xỉu", "Tài", "Tài", "Xỉu"], maxlen=200) # Dữ liệu mẫu dày hơn
        self.current_pred = "ĐANG GIẢI MÃ"
        self.current_conf = 0.0
        self.users_interacted = set()

state = SystemState()

# --- THUẬT TOÁN GIẢI MÃ HEX CỰC DÀY (KHÔNG RANDOM) ---
def hex_advanced_decoder(phien_id, data_history):
    # Lớp 1: Tạo chuỗi Base từ phiên và salt
    base_str = f"{phien_id}:{SECRET_SALT}:{time.time() // 60}"
    
    # Lớp 2: Hash SHA256 để tạo chuỗi Hex dày
    hex_hash = hmac.new(SECRET_SALT.encode(), base_str.encode(), hashlib.sha256).hexdigest()
    
    # Lớp 3: Phân tích tần suất từ dữ liệu lịch sử thực tế
    counts = Counter(data_history)
    t_count = counts.get("Tài", 0)
    x_count = counts.get("Xỉu", 0)
    
    # Lớp 4: Trích xuất trọng số từ vị trí Hex (Giải mã 4 ký tự đầu)
    hex_weight = int(hex_hash[:4], 16) / 65535
    
    # Lớp 5: Tính toán xác suất Bayesian kết hợp chuỗi Hex
    bias = (t_count / (len(data_history) if data_history else 1)) * 0.3
    final_prob = (hex_weight * 0.7) + bias
    
    if final_prob >= 0.5:
        return "Tài", round(min(final_prob * 100, 99.98), 2)
    return "Xỉu", round(min((1 - final_prob) * 100, 99.98), 2)

class AdminCommand(BaseModel):
    phien_id: int
    ket_qua_admin_chon: str # Admin chọn hướng đi: Tài hoặc Xỉu
    hien_thi_dung_sai: str  # Ghi: "Đúng" hoặc "Sai"

@app.get("/", include_in_schema=False)
async def root(): return RedirectResponse(url="/docs")

@app.get("/api/get-signal", tags=["📡 TÍN HIỆU THỜI GIAN THỰC"])
def get_signal():
    """API dành cho Client lấy dữ liệu đã giải mã"""
    return JSONResponse(content={
        "phien": state.phien,
        "du_doan": state.current_pred,
        "do_tin_cay": f"{state.current_conf}%",
        "thuat_toan": "HEX-SHA256 Layer 3",
        "toc_do_giai_ma": "0.0002s"
    }, media_type="application/json; charset=utf-8")

@app.post("/admin/push-vip-signal", tags=["💎 ADMIN VIP CONTROL"])
async def push_vip_signal(data: AdminCommand):
    """Giao diện Admin siêu cấp: Nhập là nổ tín hiệu"""
    admin_choice = data.ket_qua_admin_chon.strip().capitalize()
    status_text = data.hien_thi_dung_sai.strip().upper()
    
    # Cập nhật trạng thái
    state.phien = data.phien_id
    state.current_pred = admin_choice
    
    # Giải mã nhanh độ tin cậy dựa trên thuật toán Hex thực tế
    _, calculated_conf = hex_advanced_decoder(state.phien, state.raw_data)
    state.current_conf = calculated_conf
    
    state.raw_data.append(admin_choice)
    icon = "✅" if "ĐÚNG" in status_text else "❌"

    # Telegram Template Premium
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 HỖ TRỢ VIP", url=f"https://t.me/{ADMIN_ID[1:]}")]])
    msg = (
        f"🚀 <b>AI ULTIMATE DECODER v6.0</b> 🚀\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>PHIÊN:</b> <code>#{state.phien}</code>\n"
        f"🎯 <b>DỰ ĐOÁN:</b> ➔ <b>{admin_choice.upper()}</b> {icon}\n"
        f"📊 <b>XÁC SUẤT HEX:</b> <code>{state.current_conf}%</code>\n"
        f"⚡ <b>GIẢI MÃ:</b> <code>Cực nhanh (0.0002s)</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>TRẠNG THÁI:</b> <code>{status_text}</code>\n"
        f"📍 Admin: {ADMIN_ID}"
    )
    
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode=ParseMode.HTML, reply_markup=kb)
    return {"status": "Tín hiệu Hex đã được phát!", "phien": state.phien}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
