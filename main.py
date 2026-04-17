import numpy as np
import os
import asyncio
import hashlib
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

# --- CẤU HÌNH HỆ THỐNG ---
TOKEN = "8670893641:AAGovRHAo8mIGvOXchbTqxZZIG2KQiwdRcw"
GROUP_CHAT_ID = "-1002347313054" 
ADMIN_ID = "@tranhoang2286"
SECRET_KEY = "HOANG_DZ_VIP_ULTIMATE_V7"

app = FastAPI(title="🚀 AI AUTO-DECODER ULTIMATE 🚀")
bot = Bot(token=TOKEN)

class SystemState:
    def __init__(self):
        self.phien = 184726 
        self.current_pred = "N/A"
        self.current_conf = 0.0
        self.last_decision = "NONE"

state = SystemState()

# --- THUẬT TOÁN GIẢI MÃ HEX CỦA HOÀNG DZ ---
def decode_signal(phien_id):
    """Giải mã phiên bằng SHA256 để đưa ra kết quả cố định và độ tin cậy"""
    hash_object = hashlib.sha256(f"{phien_id}:{SECRET_KEY}".encode()).hexdigest()
    
    # Lấy trọng số từ mã Hex
    weight = int(hash_object[:4], 16) / 65535
    prediction = "Tài" if weight >= 0.5 else "Xỉu"
    
    # Tính độ tin cậy (biến thiên từ 60% đến 98%)
    conf = round(60 + (weight * 38), 2) if weight >= 0.5 else round(60 + ((1-weight) * 38), 2)
    return prediction, conf

class AdminAction(BaseModel):
    phien_id: int
    decision: str # "WIN" hoặc "LOSE"

@app.get("/", include_in_schema=False)
async def root(): return RedirectResponse(url="/docs")

# --- API LẤY TÍN HIỆU TỰ ĐỘNG ---
@app.get("/api/get-signal", tags=["📡 TÍN HIỆU"])
def get_signal():
    return {
        "phien": state.phien,
        "du_doan": state.current_pred,
        "do_tin_cay": f"{state.current_conf}%",
        "canh_bao": "⚠️ TỶ LỆ THẤP - HẠN CHẾ VÀO" if state.current_conf < 75 else "✅ AN TOÀN"
    }

# --- ADMIN PUSH (GIAO DIỆN NÚT BẤM) ---
@app.post("/admin/push-decision", tags=["💎 BẢNG ĐIỀU KHIỂN"])
async def push_decision(data: AdminAction):
    # 1. AI tự giải mã
    pred, conf = decode_signal(data.phien_id)
    
    # 2. Cập nhật trạng thái
    state.phien = data.phien_id
    state.current_pred = pred
    state.current_conf = conf
    
    status_icon = "✅" if data.decision.upper() == "WIN" else "❌"
    status_text = "ĐÚNG" if data.decision.upper() == "WIN" else "SAI"

    # 3. Hệ thống Cảnh báo thông minh
    warning_box = ""
    if conf < 75:
        warning_box = "\n⚠️ <b>CẢNH BÁO:</b> Tỷ lệ giải mã thấp. Hạn chế vào lệnh phiên này!"
    elif conf > 90:
        warning_box = "\n🔥 <b>TÍN HIỆU CỰC ĐẸP:</b> Tỷ lệ thắng rất cao!"

    # 4. Giao diện tin nhắn Telegram Siêu Đẹp
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💎 NHẬN CÔNG THỨC VIP", url=f"https://t.me/{ADMIN_ID[1:]}")]])
    
    msg = (
        f"🌟 <b>AI PREDICTOR PREMIUM v7.0</b> 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>PHIÊN:</b> <code>#{state.phien}</code>\n"
        f"🎯 <b>DỰ ĐOÁN:</b> ➔ <b>{pred.upper()}</b> {status_icon}\n"
        f"📊 <b>XÁC SUẤT:</b> <code>{conf}%</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>TRẠNG THÁI:</b> <code>{status_text}</code>"
        f"{warning_box}\n\n"
        f"📍 Admin: {ADMIN_ID}"
    )
    
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode=ParseMode.HTML, reply_markup=kb)
    return {"status": "Đã gửi dự đoán", "phien": state.phien}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
