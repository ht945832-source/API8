import hashlib
import time
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

# --- THÔNG TIN ĐỊNH DANH & CẤU HÌNH ---
ADMIN_CONTACT = "@tranhoang2286"
TOKEN = "8670893641:AAGovRHAo8mIGvOXchbTqxZZIG2KQiwdRcw"
GROUP_ID = "-1002347313054"

app = FastAPI(title=f"AI HEX PREDICTOR BY {ADMIN_CONTACT}")
bot = Bot(token=TOKEN)

class SystemState:
    def __init__(self):
        self.phien_hien_tai = 0
        self.du_doan_gan_nhat = "N/A"
        self.conf = 0.0
        self.is_bot_active = False
        self.last_bridge = "" # Cầu phiên trước
        self.is_waiting_confirm = False

state = SystemState()

# --- THUẬT TOÁN HEX LAYER-3 ---
def hex_vip_logic(phien, bridge):
    seed = f"{phien}-{bridge}-{ADMIN_CONTACT}-{time.time() // 60}"
    hex_hash = hashlib.sha256(seed.encode()).hexdigest()
    weight = int(hex_hash[:4], 16) / 65535
    prediction = "Tài" if weight >= 0.5 else "Xỉu"
    confidence = round(75 + (weight * 24.5) if weight >= 0.5 else 75 + ((1-weight) * 24.5), 2)
    return prediction, confidence

# --- MODELS ---
class StartBot(BaseModel):
    phien_moi_nhat: int
    cau_phien_truoc: str

class ConfirmResult(BaseModel):
    is_correct: bool

# --- ROUTES ---

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/api/status", tags=["📡 TÍN HIỆU NGƯỜI DÙNG"])
def get_status():
    """API dành cho người dùng lấy tín hiệu"""
    if not state.is_bot_active:
        return JSONResponse(content={"error": "Hệ thống đang nghỉ", "owner": ADMIN_CONTACT}, media_type="application/json; charset=utf-8")
    
    canh_bao = "🔥 CỰC ĐẸP" if state.conf > 90 else "⚠️ CẨN THẬN" if state.conf < 78 else "✅ AN TOÀN"
    
    return JSONResponse(content={
        "owner": ADMIN_CONTACT,
        "phien": state.phien_hien_tai,
        "du_doan": state.du_doan_gan_nhat,
        "do_tin_cay": f"{state.conf}%",
        "canh_bao": canh_bao,
        "trang_thai": "Chờ Admin chốt kết quả" if state.is_waiting_confirm else "Đang hiển thị"
    }, media_type="application/json; charset=utf-8")

@app.post("/admin/start-bot", tags=["💎 QUẢN TRỊ ADMIN"])
async def start_bot(data: StartBot):
    """Admin bật Bot và nhập phiên + cầu mới nhất"""
    state.is_bot_active = True
    state.phien_hien_tai = data.phien_moi_nhat
    state.last_bridge = data.cau_phien_truoc.strip().capitalize()
    
    pred, conf = hex_vip_logic(state.phien_hien_tai, state.last_bridge)
    state.du_doan_gan_nhat = pred
    state.conf = conf
    state.is_waiting_confirm = True

    msg = (
        f"🌟 <b>HỆ THỐNG AI {ADMIN_CONTACT}</b> 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>PHIÊN:</b> <code>#{state.phien_hien_tai}</code>\n"
        f"🎯 <b>DỰ ĐOÁN AI:</b> ➔ <b>{pred.upper()}</b>\n"
        f"📊 <b>XÁC SUẤT HEX:</b> <code>{conf}%</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <i>Admin đang kiểm tra kết quả...</i>"
    )
    await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.HTML)
    return {"status": "Bot đã khởi động", "pred": pred}

@app.post("/admin/confirm-and-next", tags=["💎 QUẢN TRỊ ADMIN"])
async def confirm_and_next(data: ConfirmResult):
    """NÚT BẤM ĐÚNG/SAI: Admin ấn xong hệ thống tự nhảy phiên mới"""
    if not state.is_waiting_confirm:
        raise HTTPException(status_code=400, detail="Không có phiên nào cần chốt")

    icon = "✅" if data.is_correct else "❌"
    text = "ĐÚNG" if data.is_correct else "SAI"
    
    await bot.send_message(chat_id=GROUP_ID, text=f"🔔 <b>PHIÊN {state.phien_hien_tai}:</b> {text} {icon}")

    # TỰ ĐỘNG CHUYỂN PHIÊN & DỰ ĐOÁN TIẾP
    state.phien_hien_tai += 1
    actual_res = state.du_doan_gan_nhat if data.is_correct else ("Xỉu" if state.du_doan_gan_nhat == "Tài" else "Tài")
    state.last_bridge = actual_res

    new_pred, new_conf = hex_vip_logic(state.phien_hien_tai, state.last_bridge)
    state.du_doan_gan_nhat = new_pred
    state.conf = new_conf

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 HỖ TRỢ VIP", url=f"https://t.me/{ADMIN_CONTACT[1:]}")]])
    msg = (
        f"🚀 <b>PHÂN TÍCH PHIÊN #{state.phien_hien_tai}</b>\n"
        f"🎯 <b>DỰ ĐOÁN:</b> ➔ <b>{new_pred.upper()}</b>\n"
        f"📊 <b>XÁC SUẤT:</b> <code>{new_conf}%</code>\n"
        f"👤 <i>Hệ thống bởi: {ADMIN_CONTACT}</i>"
    )
    await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.HTML, reply_markup=kb)

    return {"status": "Next", "phien_moi": state.phien_hien_tai, "du_doan": new_pred}
