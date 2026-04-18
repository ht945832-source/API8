import hashlib
import time
import asyncio
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

# --- THÔNG TIN ĐỊNH DANH ---
ADMIN_CONTACT = "@tranhoang2286"
TOKEN = "8670893641:AAGovRHAo8mIGvOXchbTqxZZIG2KQiwdRcw"
GROUP_ID = "-1002347313054"

app = FastAPI(title=f"AI HEX SYSTEM BY {ADMIN_CONTACT}")
bot = Bot(token=TOKEN)

class SystemState:
    def __init__(self):
        self.phien_hien_tai = 0
        self.du_doan_gan_nhat = ""
        self.conf = 0.0
        self.is_bot_active = False
        self.last_bridge = "" # Lưu cầu phiên trước
        self.is_waiting_confirm = False # Chờ admin xác nhận đúng/sai

state = SystemState()

# --- THUẬT TOÁN HEX VIP ---
def hex_vip_decoder(phien, bridge):
    """Giải mã Hex dựa trên phiên và cầu phiên trước"""
    seed = f"{phien}-{bridge}-{ADMIN_CONTACT}-{time.time() // 60}"
    hex_hash = hashlib.sha256(seed.encode()).hexdigest()
    
    # Lấy 4 ký tự hex đầu tiên để tính trọng số
    weight = int(hex_hash[:4], 16) / 65535
    prediction = "Tài" if weight >= 0.5 else "Xỉu"
    confidence = round(75 + (weight * 24.5) if weight >= 0.5 else 75 + ((1-weight) * 24.5), 2)
    
    return prediction, confidence

# --- MODELS ---
class StartSystem(BaseModel):
    phien_moi_nhat: int
    cau_phien_truoc: str # Nhập: "Tài" hoặc "Xỉu"

class ConfirmResult(BaseModel):
    is_correct: bool # True = Đúng, False = Sai

# --- ROUTES ---

@app.get("/", include_in_schema=False)
async def root(): return RedirectResponse(url="/docs")

@app.get("/api/status", tags=["📡 TÍN HIỆU THỜI GIAN THỰC"])
def get_status():
    """API để Client nhận kết quả dự đoán"""
    if not state.is_bot_active:
        return JSONResponse(content={"error": "Hệ thống đang tắt", "owner": ADMIN_CONTACT}, status_code=400)
    
    return JSONResponse(content={
        "owner": ADMIN_CONTACT,
        "phien": state.phien_hien_tai,
        "du_doan": state.du_doan_gan_nhat,
        "do_tin_cay": f"{state.conf}%",
        "trang_thai": "Đang chờ Admin chốt kết quả" if state.is_waiting_confirm else "Đang hiển thị"
    }, media_type="application/json; charset=utf-8")

@app.post("/admin/start-bot", tags=["💎 QUẢN TRỊ ADMIN"])
async def start_bot(data: StartSystem):
    """BẬT BOT: Nhập phiên và cầu gần nhất để AI bắt đầu dự đoán"""
    state.is_bot_active = True
    state.phien_hien_tai = data.phien_moi_nhat
    state.last_bridge = data.cau_phien_truoc.strip().capitalize()
    
    # AI tự động dự đoán bằng Hex VIP
    pred, conf = hex_vip_decoder(state.phien_hien_tai, state.last_bridge)
    state.du_doan_gan_nhat = pred
    state.conf = conf
    state.is_waiting_confirm = True

    # Gửi Telegram thông báo phiên mới
    msg = (
        f"🌟 <b>HỆ THỐNG AI {ADMIN_CONTACT}</b> 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>PHIÊN:</b> <code>#{state.phien_hien_tai}</code>\n"
        f"🎯 <b>DỰ ĐOÁN AI:</b> ➔ <b>{pred.upper()}</b>\n"
        f"📊 <b>XÁC SUẤT HEX:</b> <code>{conf}%</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <i>Chờ Admin xác nhận kết quả...</i>"
    )
    await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.HTML)
    
    return {"message": f"Đã bật Bot cho phiên {state.phien_hien_tai}", "ai_pred": pred}

@app.post("/admin/confirm-and-next", tags=["💎 QUẢN TRỊ ADMIN"])
async def confirm_and_next(data: ConfirmResult):
    """NÚT ẤN ĐÚNG/SAI: Sau khi ấn, hệ thống tự động cộng phiên và dự đoán tiếp"""
    if not state.is_waiting_confirm:
        raise HTTPException(status_code=400, detail="Chưa có phiên nào cần xác nhận")

    status_icon = "✅" if data.is_correct else "❌"
    status_text = "ĐÚNG" if data.is_correct else "SAI"

    # Gửi kết quả phiên vừa qua lên Telegram
    await bot.send_message(
        chat_id=GROUP_ID, 
        text=f"🔔 <b>KẾT QUẢ PHIÊN {state.phien_hien_tai}:</b> {status_text} {status_icon}\n────────────────",
        parse_mode=ParseMode.HTML
    )

    # TỰ ĐỘNG CẬP NHẬT PHIÊN MỚI
    state.phien_hien_tai += 1
    # Lấy kết quả thực tế (nếu đúng thì là pred, nếu sai thì là ngược lại)
    actual_res = state.du_doan_gan_nhat if data.is_correct else ("Xỉu" if state.du_doan_gan_nhat == "Tài" else "Tài")
    state.last_bridge = actual_res

    # AI TIẾP TỤC DỰ ĐOÁN PHIÊN TIẾP THEO
    new_pred, new_conf = hex_vip_decoder(state.phien_hien_tai, state.last_bridge)
    state.du_doan_gan_nhat = new_pred
    state.conf = new_conf

    # Gửi dự đoán mới
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 LIÊN HỆ", url=f"https://t.me/{ADMIN_CONTACT[1:]}")]])
    msg = (
        f"🚀 <b>PHÂN TÍCH PHIÊN TIẾP THEO</b>\n"
        f"🆔 <b>PHIÊN:</b> <code>#{state.phien_hien_tai}</code>\n"
        f"🎯 <b>DỰ ĐOÁN:</b> ➔ <b>{new_pred.upper()}</b>\n"
        f"📊 <b>XÁC SUẤT HEX:</b> <code>{new_conf}%</code>\n"
        f"👤 <i>Hệ thống bởi: {ADMIN_CONTACT}</i>"
    )
    await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.HTML, reply_markup=kb)

    return {"status": "Đã chuyển phiên", "new_phien": state.phien_hien_tai, "new_pred": new_pred}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
